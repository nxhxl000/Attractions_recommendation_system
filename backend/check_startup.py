#!/usr/bin/env python3
"""
Диагностический скрипт для проверки готовности FastAPI к запуску.
Проверяет наличие .env, DATABASE_URL, и возможность импорта модулей.
"""
import os
import sys
from pathlib import Path

def check_env_file():
    """Проверяет наличие .env файла."""
    root_dir = Path(__file__).parent.parent
    env_file = root_dir / ".env"
    
    if not env_file.exists():
        print("❌ Файл .env не найден в корне проекта")
        print(f"   Ожидаемый путь: {env_file}")
        print("   Создайте файл .env с содержимым:")
        print("   DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DBNAME?sslmode=require")
        return False
    
    print(f"✅ Файл .env найден: {env_file}")
    return True

def check_database_url():
    """Проверяет наличие DATABASE_URL в переменных окружения."""
    from dotenv import load_dotenv
    
    root_dir = Path(__file__).parent.parent
    load_dotenv(root_dir / ".env")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не задан в .env файле")
        return False
    
    # Маскируем пароль для безопасности
    masked_url = database_url
    if "@" in database_url:
        parts = database_url.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split(":")
            if len(user_pass) >= 2:
                masked_url = f"{user_pass[0]}:****@{parts[1]}"
    
    print(f"✅ DATABASE_URL найден: {masked_url}")
    return True

def check_database_connection():
    """Проверяет возможность подключения к базе данных."""
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    
    root_dir = Path(__file__).parent.parent
    load_dotenv(root_dir / ".env")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не задан, пропускаем проверку подключения")
        return False
    
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Подключение к базе данных успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        print("   Проверьте:")
        print("   - Правильность DATABASE_URL")
        print("   - Доступность базы данных")
        print("   - Наличие интернет-соединения (если используется облачная БД)")
        return False

def check_check_db_import():
    """Проверяет возможность импорта check_db."""
    scripts_path = Path(__file__).parent.parent / "scripts"
    if scripts_path not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    try:
        from check_db import recommend_cosine, get_data_from_db
        print("✅ Модуль check_db успешно импортирован")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта check_db: {e}")
        print(f"   Проверьте наличие файла: {scripts_path / 'check_db.py'}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при импорте check_db: {e}")
        return False

def main():
    print("=" * 60)
    print("Проверка готовности FastAPI к запуску")
    print("=" * 60)
    print()
    
    checks = [
        ("Файл .env", check_env_file),
        ("DATABASE_URL", check_database_url),
        ("Подключение к БД", check_database_connection),
        ("Импорт check_db", check_check_db_import),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n[{name}]")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ Все проверки пройдены! FastAPI должен запуститься.")
        print("\nЗапустите сервер:")
        print("  uvicorn backend.app:app --reload --port 8000")
    else:
        print("❌ Обнаружены проблемы. Исправьте их перед запуском.")
    print("=" * 60)

if __name__ == "__main__":
    main()


