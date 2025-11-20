# backend/user_cf.py

import os
import logging
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("user_cf")

# -----------------------------
# Подключение к БД
# -----------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задан в .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


# ---------------------------------------------------------
# Загружаем данные
# ---------------------------------------------------------
def load_data_from_db() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ratings_df = pd.read_sql(
        "SELECT user_id, attraction_id, rating FROM public.ratings",
        engine,
    )

    attractions_df = pd.read_sql(
        """
        SELECT id, name, city, type, transport, price, working_hours, rating, image_url
        FROM public.attractions
        """,
        engine,
    )

    # Загрузка cosine similarity из таблицы
    sim_df = pd.read_sql(
        """
        SELECT user_id_low, user_id_high, similarity
        FROM public.user_similarity
        """,
        engine,
    )

    return ratings_df, attractions_df, sim_df


# ---------------------------------------------------------
# Build user-item matrix
# ---------------------------------------------------------
def build_user_item_matrix(ratings_df: pd.DataFrame) -> pd.DataFrame:
    return ratings_df.pivot_table(
        index="user_id",
        columns="attraction_id",
        values="rating",
        aggfunc="mean",
    )


# ---------------------------------------------------------
# Получение similarity для пользователя user_id
# ---------------------------------------------------------
def load_similarity_for_user(target_user: int, sim_df: pd.DataFrame) -> pd.Series:
    """
    Возвращает Series, где index = user_id, value = similarity.
    """

    # пользователь как low
    sim_low = sim_df[sim_df["user_id_low"] == target_user][["user_id_high", "similarity"]]
    sim_low = sim_low.rename(columns={"user_id_high": "user_id"})

    # пользователь как high
    sim_high = sim_df[sim_df["user_id_high"] == target_user][["user_id_low", "similarity"]]
    sim_high = sim_high.rename(columns={"user_id_low": "user_id"})

    merged = pd.concat([sim_low, sim_high], axis=0)

    if merged.empty:
        return pd.Series(dtype=float)

    return merged.set_index("user_id")["similarity"]
    

# ---------------------------------------------------------
# Основная функция рекомендаций
# ---------------------------------------------------------
def recommend_user_based(
    user_item: pd.DataFrame,
    attractions_df: pd.DataFrame,
    sim_df: pd.DataFrame,
    user_id: int,
    top_k: int = 10,
) -> pd.DataFrame:
    if user_id not in user_item.index:
        raise ValueError(f"У пользователя {user_id} нет оценок")

    # similarity -> Series(user_id → similarity)
    sim_series = load_similarity_for_user(user_id, sim_df)

    if sim_series.empty:
        raise ValueError(f"Нет similarity данных для пользователя {user_id}")

    target_ratings = user_item.loc[user_id]

    # какие объекты пользователь не оценивал
    unrated_items = target_ratings[target_ratings.isna()].index.to_list()

    scores = []

    for attr_id in unrated_items:
        # оценки других пользователей
        other_ratings = user_item[attr_id].dropna()
        if other_ratings.empty:
            continue

        # пересечение пользователей
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
        raise ValueError("Невозможно построить рекомендации")

    # sort
    scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

    # final
    attr_ids_top = [a_id for a_id, _ in scores_sorted]
    scores_map = {a_id: sc for a_id, sc in scores_sorted}

    rec_df = attractions_df[attractions_df["id"].isin(attr_ids_top)].copy()
    rec_df["score"] = rec_df["id"].map(scores_map)
    rec_df = rec_df.sort_values("score", ascending=False)

    return rec_df


# ---------------------------------------------------------
# Главная функция для FastAPI
# ---------------------------------------------------------
def get_recommendations_for_user(user_id: int, top_k: int = 10) -> list[dict]:
    ratings_df, attractions_df, sim_df = load_data_from_db()
    user_item = build_user_item_matrix(ratings_df)
    rec_df = recommend_user_based(user_item, attractions_df, sim_df, user_id, top_k)

    return rec_df.to_dict(orient="records")
