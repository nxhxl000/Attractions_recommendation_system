import pandas as pd
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# -------------------------
# Подключение к базе данных
# -------------------------
load_dotenv()  # Загружаем переменные окружения из .env

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL не задан. Укажите его в .env (формат: postgresql+psycopg2://...)?sslmode=require"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# -------------------------
# Получение данных из базы данных
# -------------------------
def get_data_from_db():
    """Загружает данные о достопримечательностях из базы данных."""
    query = """
    SELECT 
        id,
        name,
        COALESCE(city, '') as city,
        COALESCE(type, '') as type,
        COALESCE(transport, '') as transport,
        COALESCE(price, '') as price,
        COALESCE(working_hours, '') as working_hours,
        COALESCE(rating, 0.0) as rating
    FROM public.attractions
    """
    try:
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        # Если колонки не существуют, попробуем получить только доступные колонки
        print(f"Предупреждение: {e}")
        print("Попытка получить данные с доступными колонками...")
        query_simple = "SELECT * FROM public.attractions"
        df = pd.read_sql(query_simple, engine)
        # Добавляем недостающие колонки со значениями по умолчанию
        required_columns = ['name', 'city', 'type', 'transport', 'price', 'working_hours', 'rating']
        for col in required_columns:
            if col not in df.columns:
                if col == 'rating':
                    df[col] = 0.0
                else:
                    df[col] = ''
        return df

df = get_data_from_db()

# -------------------------
# Функции-помощники для преобразования полей в признаки
# -------------------------
def transport_tokens(transport_str):
    # нормализуем и разбиваем строку транспорта
    return [t.strip().lower() for t in transport_str.replace(',', ' ').split()]

def type_tokens(type_str):
    return [t.strip().lower() for t in type_str.replace(',', ' ').split()]

def parse_working_hours_flag(wh_str, desired_period):
    # Простая эвристика: определяет, открыто ли объект в нужный период.
    # desired_period: 'morning', 'afternoon', 'evening', 'night', 'anytime'
    s = wh_str.lower()
    if 'круглосуточно' in s or 'круглосуточно' in wh_str.lower():
        return 1
    if desired_period == 'anytime':
        return 1
    # Попытка распарсить диапазон часов вида "10:00-17:00"
    try:
        if '-' in s:
            a,b = s.split('-')
            h1 = int(a.split(':')[0])
            h2 = int(b.split(':')[0])
            # normalize to 0..23, assume h2 > h1 (simplify)
            if desired_period == 'morning': # 6..11
                return int(not (h2 < 6 or h1 > 11))
            if desired_period == 'afternoon': # 12..16
                return int(not (h2 < 12 or h1 > 16))
            if desired_period == 'evening': # 17..21
                return int(not (h2 < 17 or h1 > 21))
            if desired_period == 'night': # 22..5 -> hard, treat as closed if range doesn't include night hours
                return int((h1 <= 23 and h2 >= 22) or (h1 <= 5))
    except Exception:
        return 0
    return 0

# -------------------------
# Построение словарей признаков для объектов
# -------------------------
def item_to_feature_dict(row, desired_period):
    d = {}
    # categorical multi-token fields -> one-hot tokens
    for t in transport_tokens(row['transport']):
        d[f"transport={t}"] = 1
    for t in type_tokens(row['type']):
        d[f"type={t}"] = 1
    d[f"price={row['price'].lower()}"] = 1
    d[f"city={row['city'].lower()}"] = 1
    # rating as numeric (will be scaled)
    d["rating"] = row.get("rating", 0.0)
    # working_hours match flag
    d["open_in_period"] = parse_working_hours_flag(row.get("working_hours",""), desired_period)
    return d

# -------------------------
# Функция для получения векторов и ранжирования
# -------------------------
def recommend_cosine(df, user_preferences, top_k=5):
    """
    df - DataFrame with columns: name, city, type, transport, price, working_hours, rating
    user_preferences - dict with keys: city (optional), type (optional, str), transport (optional, str),
                       price (optional), desired_period (one of 'morning','afternoon','evening','night','anytime'),
                       min_rating (optional)
    """
    desired_period = user_preferences.get("desired_period", "anytime")
    # Build feature dicts for items
    items_features = [item_to_feature_dict(row, desired_period) for _, row in df.iterrows()]
    # Build user feature dict (same tokenization logic)
    user = {
        # city preference (if provided)
    }
    if user_preferences.get("city"):
        user[f"city={user_preferences['city'].lower()}"] = 1
    if user_preferences.get("type"):
        for t in type_tokens(user_preferences["type"]):
            user[f"type={t}"] = 1
    if user_preferences.get("transport"):
        for t in transport_tokens(user_preferences["transport"]):
            user[f"transport={t}"] = 1
    if user_preferences.get("price"):
        user[f"price={user_preferences['price'].lower()}"] = 1
    # rating: use user's minimum rating as a preference (optional)
    user["rating"] = user_preferences.get("min_rating", df['rating'].max())  # prefer higher by default
    # working hours
    user["open_in_period"] = 1  # user wants it open in the chosen period

    # Vectorize dicts
    dv = DictVectorizer(sparse=False)
    X = dv.fit_transform(items_features + [user])  # last row = user
    X_items = X[:-1, :]
    X_user = X[-1, :].reshape(1, -1)

    # Scale rating column to [0,1] to avoid dominating by raw rating
    # find index of 'rating' feature if exists
    feature_names = dv.get_feature_names_out()
    if "rating" in feature_names:
        idx = list(feature_names).index("rating")
        scaler = MinMaxScaler()
        # scale only rating column
        X_items[:, idx:idx+1] = scaler.fit_transform(X_items[:, idx:idx+1])
        X_user[:, idx:idx+1] = scaler.transform(X_user[:, idx:idx+1])

    # Compute cosine similarity
    sims = cosine_similarity(X_items, X_user).reshape(-1)
    df_result = df.copy()
    df_result['score'] = sims
    # Apply optional min_rating filter
    if user_preferences.get("min_rating") is not None:
        df_result = df_result[df_result['rating'] >= user_preferences['min_rating']]
    df_sorted = df_result.sort_values('score', ascending=False).reset_index(drop=True)
    return df_sorted.head(top_k)

# -------------------------
# Пример использования
# -------------------------
user_prefs = {
    "city": "Москва",
    "type": "Современная",
    "transport": "Пешком",
    "price": "Платно",
    "desired_period": "night",
    "min_rating": 0.0
}

top = recommend_cosine(df, user_prefs, top_k=10)
print(top[['name', 'city', 'type', 'transport', 'price', 'working_hours', 'rating', 'score']])
