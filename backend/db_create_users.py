import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -----------------------------
# ЛОГИРОВАНИЕ (RU)
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("db_create_users")

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
# SQL: создание таблицы users
# -----------------------------
DDL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS public.users (
    id              SERIAL PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE public.users IS 'Пользователи системы рекомендаций';
COMMENT ON COLUMN public.users.id IS 'Уникальный идентификатор пользователя';
COMMENT ON COLUMN public.users.username IS 'Логин пользователя (уникальный)';
COMMENT ON COLUMN public.users.hashed_password IS 'Хэш пароля пользователя';
COMMENT ON COLUMN public.users.is_admin IS 'Флаг: является ли пользователь администратором';
"""

# SQL: сдвиг sequence на 51
SQL_SET_SEQUENCE = """
SELECT setval(
    pg_get_serial_sequence('public.users', 'id'),
    30,
    true
);
"""

def ensure_users_table():
    """Создаёт таблицу пользователей, если её нет, и сдвигает sequence до 51."""
    with engine.begin() as conn:
        log.info("Создаю таблицу public.users (если её нет)...")
        conn.execute(text(DDL_CREATE_USERS))
        log.info("Таблица public.users готова.")

        # Сдвиг sequence: чтобы следующий id был 51
        log.info("Сдвигаю sequence users.id на старт с 31...")
        conn.execute(text(SQL_SET_SEQUENCE))
        log.info("Sequence успешно сдвинут: следующий id = 31.")


# -----------------------------
# MAIN
# -----------------------------
def main():
    try:
        ensure_users_table()
    except Exception as e:
        log.error("Непредвиденная ошибка: %s", str(e))
        raise SystemExit(1)
    else:
        log.info("✅ Таблица public.users успешно создана / обновлена.")
        log.info("   Следующий пользователь получит id = 31.")

if __name__ == "__main__":
    main()
