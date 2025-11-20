# scripts/db_create_planned_visits.py

import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -----------------------------
# ЛОГИРОВАНИЕ
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("db_create_planned_visits")

# -----------------------------
# ЗАГРУЗКА .env
# -----------------------------
load_dotenv()  # подтянет DATABASE_URL из .env

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit(
        "❌ Ошибка: переменная окружения DATABASE_URL не задана. "
        "Укажите её в .env (postgresql+psycopg2://...)?sslmode=require"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# -----------------------------
# СОЗДАНИЕ ТАБЛИЦЫ public.planned_visits
# -----------------------------
DDL_CREATE_PLANNED_VISITS = """
CREATE TABLE IF NOT EXISTS public.planned_visits (
    user_id        INTEGER NOT NULL,
    attraction_id  INTEGER NOT NULL,
    added_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT planned_visits_pk
        PRIMARY KEY (user_id, attraction_id),

    CONSTRAINT planned_visits_user_fk
        FOREIGN KEY (user_id)
        REFERENCES public.users(id)
        ON DELETE CASCADE,

    CONSTRAINT planned_visits_attraction_fk
        FOREIGN KEY (attraction_id)
        REFERENCES public.attractions(id)
        ON DELETE CASCADE
);

COMMENT ON TABLE public.planned_visits IS 'Список достопримечательностей, которые пользователь планирует посетить';
COMMENT ON COLUMN public.planned_visits.user_id IS 'ID пользователя';
COMMENT ON COLUMN public.planned_visits.attraction_id IS 'ID достопримечательности';
COMMENT ON COLUMN public.planned_visits.added_at IS 'Дата и время, когда пользователь добавил достопримечательность в планы';
"""

def ensure_planned_visits_table():
    """Создаёт таблицу planned_visits, если её нет."""
    with engine.begin() as conn:
        log.info("Создаю таблицу public.planned_visits (если её нет)...")
        conn.execute(text(DDL_CREATE_PLANNED_VISITS))
        log.info("Таблица public.planned_visits готова.")

# -----------------------------
# MAIN
# -----------------------------
def main():
    try:
        ensure_planned_visits_table()
    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Таблица public.planned_visits успешно создана (или уже существовала).")

if __name__ == "__main__":
    main()
