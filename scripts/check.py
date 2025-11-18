import pandas as pd
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------
# Пример данных (замени на свой DataFrame)
# -------------------------
data = [
    {"name": "Красная площадь", "city": "Москва", "type": "Историческая",
     "transport": "Пешком, Авто", "price": "Бесплатно", "working_hours": "Круглосуточно", "rating": 5.0},
    {"name": "Кремль", "city": "Москва", "type": "Архитектурная",
     "transport": "Пешком, Авто", "price": "Платно", "working_hours": "10:00-17:00", "rating": 5.0},
    {"name": "Эрмитаж", "city": "Санкт-Петербург", "type": "Культурная",
     "transport": "Общественный транспорт, Авто, пешком", "price": "Платно", "working_hours": "11:00-19:00", "rating": 5.0},
    {"name": "Спас на Крови", "city": "Санкт-Петербург", "type": "Архитектурная, культурная",
     "transport": "Пешком, Авто, общественный транспорт", "price": "Платно", "working_hours": "10:00-17:30", "rating": 5.0},
    {"name": "Казанский Кремль", "city": "Казань", "type": "Архитектурная",
     "transport": "Пешком, Авто", "price": "Платно", "working_hours": "10:00-22:00", "rating": 5.0},
]

df = pd.DataFrame(data)

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
    "type": "Архитектурная",
    "transport": "Пешком",
    "price": "Бесплатно",
    "desired_period": "19:00-21:00",
    "min_rating": 4.0
}

top = recommend_cosine(df, user_prefs, top_k=10)
print(top[['name', 'city', 'type', 'transport', 'price', 'working_hours', 'rating', 'score']])
