import os
import logging

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# ЛОГИРОВАНИЕ
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("user_cf")

# -----------------------------
# БД
# -----------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit(
        "❌ DATABASE_URL не задан. Укажи его в .env (postgresql+psycopg2://...)"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


def load_data_from_db() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Загружает:
    - ratings: user_id, attraction_id, rating
    - attractions: id, name, city, type, transport, price, working_hours, rating
    """
    log.info("Загружаю ratings...")
    ratings_df = pd.read_sql(
        "SELECT user_id, attraction_id, rating FROM public.ratings",
        engine,
    )

    if ratings_df.empty:
        raise SystemExit("❌ Таблица public.ratings пуста")

    log.info("Загружаю attractions...")
    attractions_df = pd.read_sql(
        """
        SELECT id, name, city, type, transport, price, working_hours, rating
        FROM public.attractions
        """,
        engine,
    )
    if attractions_df.empty:
        raise SystemExit("❌ Таблица public.attractions пуста")

    log.info(
        "✔ ratings: %d строк, attractions: %d строк",
        len(ratings_df),
        len(attractions_df),
    )
    return ratings_df, attractions_df


def build_user_item_matrix(ratings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Строит user-item матрицу:
    строки — user_id, столбцы — attraction_id, значения — rating.
    """
    user_item = ratings_df.pivot_table(
        index="user_id",
        columns="attraction_id",
        values="rating",
        aggfunc="mean",
    )
    log.info(
        "Матрица user-item: %d пользователей × %d объектов",
        user_item.shape[0],
        user_item.shape[1],
    )
    return user_item


def recommend_user_based(
    user_item: pd.DataFrame,
    attractions_df: pd.DataFrame,
    user_id: int,
    top_k: int = 10,
) -> pd.DataFrame:
    """
    User-based CF:
    - считает косинусное сходство между пользователями
    - предсказывает оценки для объектов, которые user_id ещё не оценивал
    - возвращает топ-k объектов с полями attractions + score
    """
    if user_id not in user_item.index:
        raise ValueError(
            f"У пользователя {user_id} нет оценок в матрице user-item"
        )

    # --- 1. заполняем NaN нулём для cosine_similarity ---
    user_item_filled = user_item.fillna(0.0)

    user_ids = user_item_filled.index.to_list()
    sim_matrix = cosine_similarity(user_item_filled.values)

    try:
        target_idx = user_ids.index(user_id)
    except ValueError:
        raise ValueError(f"Пользователь {user_id} отсутствует в матрице")

    target_sims = sim_matrix[target_idx]

    # --- 2. какие объекты пользователь ещё не оценивал ---
    target_ratings = user_item.loc[user_id]
    unrated_items = target_ratings[target_ratings.isna()].index.to_list()
    if not unrated_items:
        raise ValueError("Пользователь уже оценил все объекты")

    # Series: user_id -> similarity
    sim_series = pd.Series(target_sims, index=user_ids)
    # себя исключаем
    sim_series = sim_series.drop(index=user_id)

    scores: list[tuple[int, float]] = []

    for attr_id in unrated_items:
        # оценки других пользователей для этой достопримечательности
        other_ratings = user_item[attr_id].dropna()
        if other_ratings.empty:
            continue

        common_users = other_ratings.index.intersection(sim_series.index)
        if common_users.empty:
            continue

        sims = sim_series.loc[common_users]
        ratings_vals = other_ratings.loc[common_users]

        denom = sims.abs().sum()
        if denom == 0:
            continue

        score = float((sims * ratings_vals).sum() / denom)
        scores.append((int(attr_id), score))

    if not scores:
        raise ValueError("Не удалось посчитать ни одной рекомендации")

    # сортируем и берём топ-k
    scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
    attr_ids_top = [a_id for a_id, _ in scores_sorted]
    scores_map = {a_id: sc for a_id, sc in scores_sorted}

    rec_df = attractions_df[attractions_df["id"].isin(attr_ids_top)].copy()
    rec_df["score"] = rec_df["id"].map(scores_map)
    rec_df = rec_df.sort_values("score", ascending=False)

    return rec_df


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="User-based рекомендации для пользователя"
    )
    parser.add_argument("--user-id", type=int, required=True, help="ID пользователя")
    parser.add_argument(
        "--top-k", type=int, default=10, help="Сколько рекомендаций вернуть"
    )
    args = parser.parse_args()

    ratings_df, attractions_df = load_data_from_db()
    user_item = build_user_item_matrix(ratings_df)

    try:
        rec_df = recommend_user_based(
            user_item, attractions_df, user_id=args.user_id, top_k=args.top_k
        )
    except Exception as e:
        log.error("Ошибка при расчёте рекомендаций: %s", e)
        raise SystemExit(1)

    # Красиво печатаем результат в консоль
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    print(
        f"\nРекомендации для пользователя {args.user_id} (top-{args.top_k}):\n"
    )
    print(
        rec_df[
            ["id", "name", "city", "type", "transport", "price", "working_hours", "rating", "score"]
        ]
    )


if __name__ == "__main__":
    main()