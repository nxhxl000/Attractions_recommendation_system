import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -----------------------------
# ЛОГИРОВАНИЕ (RU)
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("db_update_create_trigger")

# -----------------------------
# ЗАГРУЗКА .env
# -----------------------------
load_dotenv()  # подтянет DATABASE_URL из .env

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("❌ Ошибка: переменная окружения DATABASE_URL не задана. "
                     "Укажите её в .env (postgresql+psycopg2://...)?sslmode=require")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# -----------------------------
# ОБНОВЛЕНИЕ РЕЙТИНГА В public.attractions
# -----------------------------
def update_ratings_for_attractions():
    """Заполняет поле rating в таблице attractions на основе данных из таблицы ratings."""
    update_rating_query = """
    UPDATE public.attractions
    SET rating = ROUND(subquery.avg_rating, 1)
    FROM (
        SELECT attraction_id, AVG(rating) AS avg_rating
        FROM public.ratings
        GROUP BY attraction_id
    ) AS subquery
    WHERE public.attractions.id = subquery.attraction_id;
    """
    
    with engine.begin() as conn:
        log.info("Заполняю рейтинг для достопримечательностей...")
        conn.execute(text(update_rating_query))
    log.info("Рейтинг для достопримечательностей успешно обновлен.")

# -----------------------------
# СОЗДАНИЕ ФУНКЦИИ И ТРИГГЕРА ДЛЯ ОБНОВЛЕНИЯ РЕЙТИНГА
# -----------------------------
def create_trigger():
    """Создаёт функцию и триггер для обновления рейтинга в public.attractions."""
    create_function_query = """
    CREATE OR REPLACE FUNCTION update_attraction_rating()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Обновляем рейтинг для аттракциона после вставки, обновления или удаления записи в ratings
        UPDATE public.attractions
        SET rating = ROUND(subquery.avg_rating, 1)
        FROM (
            SELECT attraction_id, AVG(rating) AS avg_rating
            FROM public.ratings
            GROUP BY attraction_id
        ) AS subquery
        WHERE public.attractions.id = subquery.attraction_id;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """

    create_trigger_query = """
    CREATE TRIGGER update_attraction_rating_trigger
    AFTER INSERT OR UPDATE OR DELETE ON public.ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_attraction_rating();
    """
    
    with engine.begin() as conn:
        log.info("Создаю функцию и триггер для обновления рейтинга...")
        conn.execute(text(create_function_query))
        conn.execute(text(create_trigger_query))
        log.info("Функция и триггер успешно созданы.")

# -----------------------------
# ОСНОВНОЙ ПРОЦЕСС
# -----------------------------
def main():
    try:
        # Обновляем рейтинг для достопримечательностей на основе данных из таблицы ratings
        update_ratings_for_attractions()

        # Создаём функцию и триггер для обновления рейтинга
        create_trigger()

    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Рейтинг успешно обновлен и триггер для обновления рейтинга создан.")

if __name__ == "__main__":
    main()
