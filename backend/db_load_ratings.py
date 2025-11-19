import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------
# ЛОГИРОВАНИЕ (RU)
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("db_load_ratings")

# -----------------------------
# ЗАГРУЗКА .env
# -----------------------------
load_dotenv()  # подтянет DATABASE_URL из .env

BASE_DIR = Path(__file__).resolve().parent  # .../backend
CSV_PATH = BASE_DIR.parent / "ratings_table.csv"

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("❌ Ошибка: переменная окружения DATABASE_URL не задана. "
                     "Укажите её в .env (postgresql+psycopg2://...)?sslmode=require")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# -----------------------------
# СОЗДАНИЕ ТАБЛИЦЫ public.ratings
# -----------------------------
DDL_CREATE_RATINGS = """
CREATE TABLE IF NOT EXISTS public.ratings (
  attraction_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  rating INTEGER NOT NULL,
  PRIMARY KEY (attraction_id, user_id)
);

COMMENT ON TABLE public.ratings IS 'Оценки пользователей для достопримечательностей';
COMMENT ON COLUMN public.ratings.attraction_id IS 'Идентификатор достопримечательности';
COMMENT ON COLUMN public.ratings.user_id IS 'Идентификатор пользователя';
COMMENT ON COLUMN public.ratings.rating IS 'Оценка пользователя для достопримечательности';
"""

def ensure_ratings_table():
    """Создаёт таблицу для рейтингов, если её нет."""
    with engine.begin() as conn:
        log.info("Создаю таблицу public.ratings (если её нет)...")
        conn.execute(text(DDL_CREATE_RATINGS))

# -----------------------------
# ЗАГРУЗКА ДАННЫХ ИЗ CSV
# -----------------------------
def load_ratings_from_csv(csv_file_path):
    """Загружает данные рейтингов из CSV файла в БД."""
    df = pd.read_csv(csv_file_path)
    log.info(f"Загружено {len(df)} записей из {csv_file_path}")

    # Сохраняем данные в таблицу ratings
    with engine.begin() as conn:
        for _, row in df.iterrows():
            # Преобразуем numpy.int64 в обычные int
            attraction_id = row["attraction_id"].item()
            user_id = row["user_id"].item()
            rating = row["rating"].item()

            conn.execute(
                text("INSERT INTO public.ratings (attraction_id, user_id, rating) "
                     "VALUES (:attraction_id, :user_id, :rating) "
                     "ON CONFLICT (attraction_id, user_id) DO NOTHING"),
                {"attraction_id": attraction_id, "user_id": user_id, "rating": rating}
            )
    log.info(f"Данные из {csv_file_path} успешно загружены в таблицу public.ratings")

def main():
    try:
        # Создаём таблицу для рейтингов, если её нет
        ensure_ratings_table()
        
        # Загружаем данные из CSV в базу данных
        load_ratings_from_csv(CSV_PATH)
    
    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Данные успешно загружены в таблицу public.ratings.")

if __name__ == "__main__":
    main()