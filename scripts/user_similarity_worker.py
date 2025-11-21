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
log = logging.getLogger("user_similarity_worker")

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
# DDL: ОЧЕРЕДЬ + ТРИГГЕР НА ratings
# -----------------------------
DDL_CREATE_QUEUE_AND_TRIGGER = """
-- 1) Таблица-очередь для задач пересчёта
CREATE TABLE IF NOT EXISTS public.user_similarity_recalc_queue (
    id         BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.user_similarity_recalc_queue IS
    'Очередь задач на пересчёт матрицы похожести пользователей';

-- 2) Функция-триггер: при любом изменении ratings добавляем запись в очередь
CREATE OR REPLACE FUNCTION public.notify_user_similarity_recalc()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_similarity_recalc_queue DEFAULT VALUES;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3) Триггер на ratings (после INSERT/UPDATE/DELETE, один раз на statement)
DROP TRIGGER IF EXISTS trg_user_similarity_recalc ON public.ratings;

CREATE TRIGGER trg_user_similarity_recalc
AFTER INSERT OR UPDATE OR DELETE ON public.ratings
FOR EACH STATEMENT
EXECUTE FUNCTION public.notify_user_similarity_recalc();
"""


def ensure_queue_and_trigger() -> None:
    """Создаёт очередь и триггер на ratings (идемпотентно)."""
    with engine.begin() as conn:
        log.info("Проверяю / создаю очередь и триггер на public.ratings ...")
        conn.execute(text(DDL_CREATE_QUEUE_AND_TRIGGER))
    log.info("✔ Очередь user_similarity_recalc_queue и триггер настроены.")


# -----------------------------
# ЗАГРУЗКА РЕЙТИНГОВ
# -----------------------------
def load_ratings() -> pd.DataFrame:
    """Загружает таблицу ratings (user_id, attraction_id, rating)."""
    log.info("Загружаю данные из public.ratings ...")
    df = pd.read_sql(
        "SELECT user_id, attraction_id, rating FROM public.ratings",
        engine,
    )
    if df.empty:
        raise SystemExit("❌ Таблица public.ratings пуста — нечего считать.")
    log.info("✔ ratings: %d строк", len(df))
    return df


# -----------------------------
# ПОСТРОЕНИЕ USER-ITEM МАТРИЦЫ
# -----------------------------
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


# -----------------------------
# РАСЧЁТ КОСИНУСНОЙ ПОХОЖЕСТИ
# -----------------------------
def compute_pairwise_similarity(user_item: pd.DataFrame) -> pd.DataFrame:
    """
    Считает cosine similarity между всеми пользователями и возвращает
    DataFrame с колонками:
        user_id_low, user_id_high, similarity

    Каждая пара (low, high) хранится один раз (симметрию не дублируем).
    """
    if user_item.shape[0] < 2:
        raise SystemExit("❌ Недостаточно пользователей для расчёта похожести (< 2).")

    user_item_filled = user_item.fillna(0.0)
    user_ids = user_item_filled.index.to_list()
    log.info("Считаю cosine similarity для %d пользователей ...", len(user_ids))

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


# -----------------------------
# СОХРАНЕНИЕ В public.user_similarity
# -----------------------------
def save_user_similarity(sim_df: pd.DataFrame) -> None:
    """
    Полностью перезаписывает таблицу public.user_similarity данными из sim_df.

    Таблица public.user_similarity ДОЛЖНА уже существовать (создана другим скриптом)
    с колонками:
        user_id_low INTEGER
        user_id_high INTEGER
        similarity NUMERIC / DOUBLE PRECISION
    """
    if sim_df.empty:
        log.warning(
            "⚠️ DataFrame с похожестями пуст — таблица public.user_similarity не будет обновлена."
        )
        return

    records = sim_df.to_dict(orient="records")

    with engine.begin() as conn:
        log.info("Очищаю таблицу public.user_similarity ...")
        conn.execute(text("TRUNCATE TABLE public.user_similarity"))

        log.info("Вставляю новые данные (уникальные пары пользователей) ...")
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

    log.info("✅ Таблица public.user_similarity успешно обновлена.")


# -----------------------------
# РАБОТА С ОЧЕРЕДЬЮ
# -----------------------------
def queue_has_jobs_and_clear() -> bool:
    """
    Проверяет, есть ли записи в очереди user_similarity_recalc_queue.
    Если есть — удаляет их (считаем, что сейчас всё пересчитаем) и возвращает True.
    Если нет — возвращает False.
    """
    with engine.begin() as conn:
        res = conn.execute(
            text("SELECT id FROM public.user_similarity_recalc_queue ORDER BY id DESC LIMIT 1")
        )
        row = res.fetchone()
        if not row:
            log.info("Очередь user_similarity_recalc_queue пуста — пересчёт не требуется.")
            return False

        last_id = row[0]
        log.info("Найдено задачи в очереди (максимальный id = %s). Очищаю очередь ...", last_id)
        conn.execute(
            text("DELETE FROM public.user_similarity_recalc_queue WHERE id <= :last_id"),
            {"last_id": last_id},
        )
    return True


# -----------------------------
# MAIN
# -----------------------------
def main():
    try:
        # 1. Настраиваем очередь и триггер (идемпотентно)
        ensure_queue_and_trigger()

        # 2. Проверяем, есть ли задачи на пересчёт
        if not queue_has_jobs_and_clear():
            # Ничего не изменилось в ratings — выходим
            return

        # 3. Загружаем рейтинги и пересчитываем матрицу
        ratings_df = load_ratings()
        user_item = build_user_item_matrix(ratings_df)
        sim_df = compute_pairwise_similarity(user_item)

        # 4. Сохраняем в user_similarity
        save_user_similarity(sim_df)

    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Матрица похожести пользователей успешно пересчитана и сохранена.")


if __name__ == "__main__":
    main()