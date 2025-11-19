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
log = logging.getLogger("db_load_attractions")

# -----------------------------
# ЗАГРУЗКА .env
# -----------------------------
load_dotenv()  # подтянет DATABASE_URL из .env

BASE_DIR = Path(__file__).resolve().parent  # .../backend
CSV_PATH = BASE_DIR.parent / "attractions.csv"

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("❌ Ошибка: переменная окружения DATABASE_URL не задана. "
                     "Укажите её в .env (postgresql+psycopg2://...)?sslmode=require")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# -----------------------------
# СОЗДАНИЕ ТАБЛИЦЫ public.attractions
# -----------------------------
DDL_CREATE_ATTRACTIONS = """
CREATE TABLE IF NOT EXISTS public.attractions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    type TEXT NOT NULL,
    transport TEXT NOT NULL,
    price TEXT NOT NULL,
    working_hours TEXT NOT NULL,
    rating FLOAT 
);

COMMENT ON TABLE public.attractions IS 'Достопримечательности с их данными';
COMMENT ON COLUMN public.attractions.id IS 'Уникальный идентификатор достопримечательности';
COMMENT ON COLUMN public.attractions.name IS 'Название достопримечательности';
COMMENT ON COLUMN public.attractions.city IS 'Город, где расположена достопримечательность';
COMMENT ON COLUMN public.attractions.type IS 'Тип достопримечательности';
COMMENT ON COLUMN public.attractions.transport IS 'Тип транспорта, используемого для посещения';
COMMENT ON COLUMN public.attractions.price IS 'Цена на посещение достопримечательности';
COMMENT ON COLUMN public.attractions.working_hours IS 'Часы работы достопримечательности';
COMMENT ON COLUMN public.attractions.rating IS 'Рейтинг достопримечательности';
"""

def ensure_attractions_table():
    """Создаёт таблицу для достопримечательностей, если её нет."""
    with engine.begin() as conn:
        log.info("Создаю таблицу public.attractions (если её нет)...")
        conn.execute(text(DDL_CREATE_ATTRACTIONS))

# -----------------------------
# ЗАГРУЗКА ДАННЫХ ИЗ CSV
# -----------------------------
def load_attractions_from_csv(csv_file_path):
    """Загружает данные достопримечательностей из CSV файла в БД."""
    try:
        # Чтение CSV с указанием разделителя и обработка ошибок
        df = pd.read_csv(csv_file_path, sep=';', on_bad_lines='skip')
        log.info(f"Загружено {len(df)} записей из {csv_file_path}")
    except Exception as e:
        log.error(f"Ошибка при чтении CSV файла: {e}")
        raise SystemExit(1)

    # Сохраняем данные в таблицу attractions (без поля rating)
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("INSERT INTO public.attractions (name, city, type, transport, price, working_hours) "
                     "VALUES (:name, :city, :type, :transport, :price, :working_hours)"),
                {
                    "name": row["name"],
                    "city": row["city"],
                    "type": row["type"],
                    "transport": row["transport"],
                    "price": row["price"],
                    "working_hours": row["working_hours"]
                }
            )
    log.info(f"Данные из {csv_file_path} успешно загружены в таблицу public.attractions")

def main():
    try:
        # Создаём таблицу для достопримечательностей, если её нет
        ensure_attractions_table()

        # Загружаем данные из CSV в базу данных
        load_attractions_from_csv(CSV_PATH)
    
    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Данные успешно загружены в таблицу public.attractions.")

if __name__ == "__main__":
    main()
