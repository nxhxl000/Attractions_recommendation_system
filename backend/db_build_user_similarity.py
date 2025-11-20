import os
import logging

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# ЛОГИРОВАНИЕ (RU)
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("db_build_user_similarity")

# -----------------------------
# ЗАГРУЗКА .env
# -----------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit(
        "❌ Ошибка: переменная окружения DATABASE_URL не задана. "
        "Укажите её в .env (postgresql+psycopg2://...)?sslmode=require"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# -----------------------------
# DDL: СОЗДАНИЕ ТАБЛИЦЫ public.user_similarity
# -----------------------------
DDL_CREATE_USER_SIMILARITY = """
CREATE TABLE IF NOT EXISTS public.user_similarity (
    user_id_low   INTEGER NOT NULL,
    user_id_high  INTEGER NOT NULL,
    similarity    NUMERIC(4,3) NOT NULL,
    PRIMARY KEY (user_id_low, user_id_high)
);

COMMENT ON TABLE public.user_similarity IS 'Схожесть пар пользователей (симметричная, без дублей)';
COMMENT ON COLUMN public.user_similarity.user_id_low IS 'Меньший ID из пары пользователей';
COMMENT ON COLUMN public.user_similarity.user_id_high IS 'Больший ID из пары пользователей';
COMMENT ON COLUMN public.user_similarity.similarity IS 'Косинусное сходство между пользователями';
"""


def ensure_user_similarity_table() -> None:
    """Создаёт таблицу user_similarity, если её ещё нет."""
    with engine.begin() as conn:
        log.info("Создаю таблицу public.user_similarity (если её нет)...")
        conn.execute(text(DDL_CREATE_USER_SIMILARITY))
        log.info("Таблица public.user_similarity готова.")


def load_ratings() -> pd.DataFrame:
    """Загружает таблицу ratings (user_id, attraction_id, rating)."""
    log.info("Загружаю данные из public.ratings...")
    df = pd.read_sql(
        "SELECT user_id, attraction_id, rating FROM public.ratings",
        engine,
    )
    if df.empty:
        raise SystemExit("❌ Таблица public.ratings пуста — нечего считать.")
    log.info("✔ ratings: %d строк", len(df))
    return df


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


def compute_pairwise_similarity(user_item: pd.DataFrame) -> pd.DataFrame:
    """
    Считает cosine similarity между всеми пользователями
    и возвращает DataFrame с колонками:
    user_id_low, user_id_high, similarity
    (каждая пара хранится один раз, без зеркальных дублей).
    """
    if user_item.shape[0] < 2:
        raise SystemExit("❌ Недостаточно пользователей для расчёта похожести (< 2).")

    user_item_filled = user_item.fillna(0.0)

    user_ids = user_item_filled.index.to_list()
    log.info("Считаю cosine similarity для %d пользователей...", len(user_ids))

    sim_matrix = cosine_similarity(user_item_filled.values)

    rows: list[dict] = []

    n = len(user_ids)
    for i in range(n):
        for j in range(i + 1, n):
            uid_i = int(user_ids[i])
            uid_j = int(user_ids[j])
            sim_val = float(sim_matrix[i, j])

            low = min(uid_i, uid_j)
            high = max(uid_i, uid_j)

            rows.append(
                {
                    "user_id_low": low,
                    "user_id_high": high,
                    "similarity": sim_val,
                }
            )

    sim_df = pd.DataFrame(rows)
    log.info("Итоговых уникальных пар (low, high): %d", len(sim_df))
    return sim_df


def save_user_similarity(sim_df: pd.DataFrame) -> None:
    """Полностью перезаписывает таблицу public.user_similarity данными из sim_df."""
    if sim_df.empty:
        log.warning("⚠️ DataFrame с похожестями пуст — таблица user_similarity не будет обновлена.")
        return

    records = sim_df.to_dict(orient="records")

    with engine.begin() as conn:
        log.info("Очищаю таблицу public.user_similarity...")
        conn.execute(text("TRUNCATE TABLE public.user_similarity"))

        log.info("Вставляю новые данные (уникальные пары пользователей)...")
        batch_size = 1000
        for start in range(0, len(records), batch_size):
            chunk = records[start : start + batch_size]
            conn.execute(
                text(
                    """
                    INSERT INTO public.user_similarity (user_id_low, user_id_high, similarity)
                    VALUES (:user_id_low, :user_id_high, :similarity)
                    """
                ),
                chunk,
            )

    log.info("✅ Таблица public.user_similarity успешно заполнена.")


def main():
    try:
        ensure_user_similarity_table()

        ratings_df = load_ratings()
        user_item = build_user_item_matrix(ratings_df)
        sim_df = compute_pairwise_similarity(user_item)
        save_user_similarity(sim_df)

    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Матрица похожести пользователей успешно пересчитана и сохранена.")


if __name__ == "__main__":
    main()
