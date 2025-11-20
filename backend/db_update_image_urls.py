import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("db_update_image_urls")


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit(
        "❌ Ошибка: переменная окружения DATABASE_URL не задана. "
        "Укажите её в .env (postgresql+psycopg2://...)?sslmode=require"
    )

BASE_DIR = Path(__file__).resolve().parent  # .../backend
IMAGE_URLS_FILE = BASE_DIR.parent / "image_urls.txt"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


def load_image_urls(path: str) -> dict[int, str]:
    if not os.path.exists(path):
        raise SystemExit(f"❌ Файл с URL не найден: {path}")

    image_urls: dict[int, str] = {}

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            original_line = line.rstrip("\n")
            line = line.strip()

            # пропускаем пустые строки и комментарии
            if not line or line.startswith("#"):
                continue

            # ожидаем двоеточие
            if ":" not in line:
                log.warning(
                    f"⚠️ В строке {line_num} нет двоеточия, пропускаю: {original_line!r}"
                )
                continue

            id_part, value_part = line.split(":", maxsplit=1)
            id_part = id_part.strip()
            value_part = value_part.strip()

            # убираем возможную запятую в конце
            if value_part.endswith(","):
                value_part = value_part[:-1].strip()

            # убираем кавычки (одинарные или двойные)
            if (
                (value_part.startswith('"') and value_part.endswith('"'))
                or (value_part.startswith("'") and value_part.endswith("'"))
            ):
                value_part = value_part[1:-1].strip()

            # парсим id
            try:
                attraction_id = int(id_part)
            except ValueError:
                log.warning(
                    f"⚠️ Некорректный id в строке {line_num} (не int): {id_part!r}"
                )
                continue

            url = value_part
            if not url:
                log.info(f"Пропускаю id={attraction_id} (строка {line_num}): пустой URL")
                continue

            image_urls[attraction_id] = url

    if not image_urls:
        log.warning("⚠️ В файле не найдено ни одной валидной пары id → url.")

    log.info(f"Загружено {len(image_urls)} URL из файла {path}")
    return image_urls


def ensure_image_url_column():
    """Добавляем колонку image_url, если её ещё нет."""
    with engine.begin() as conn:
        log.info("Проверяю наличие колонки image_url...")
        conn.execute(
            text(
                """
                ALTER TABLE public.attractions
                ADD COLUMN IF NOT EXISTS image_url TEXT;
                """
            )
        )
        log.info("Колонка image_url готова.")


def update_image_urls(image_urls: dict[int, str]):
    """Обновляет image_url по id из image_urls."""
    if not image_urls:
        log.warning("⚠️ Словарь image_urls пуст — обновлять нечего.")
        return

    with engine.begin() as conn:
        for attraction_id, url in image_urls.items():
            if not url:
                log.info(f"Пропускаю id={attraction_id}: пустой URL")
                continue

            result = conn.execute(
                text(
                    """
                    UPDATE public.attractions
                    SET image_url = :url
                    WHERE id = :id
                    """
                ),
                {"id": attraction_id, "url": url},
            )

            if result.rowcount == 0:
                log.warning(f"⚠️ Не нашлась строка с id={attraction_id}")
            else:
                log.info(f"✅ Обновлён id={attraction_id}")

    log.info("🎉 Все URL обработаны.")


def main():
    ensure_image_url_column()
    image_urls = load_image_urls(IMAGE_URLS_FILE)
    update_image_urls(image_urls)


if __name__ == "__main__":
    main()
