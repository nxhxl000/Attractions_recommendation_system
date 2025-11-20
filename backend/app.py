# backend/app.py
import os
import sys
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    create_engine,
    select,
    func,
)
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
import secrets

from dotenv import load_dotenv
load_dotenv()

# Add scripts directory to path to import check_db (lazy import)
scripts_path = os.path.join(os.path.dirname(__file__), '..', 'scripts')
scripts_path = os.path.abspath(scripts_path)
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# Lazy import to avoid startup errors if check_db has issues
def _import_recommendation_functions():
    """Lazy import of recommendation functions to avoid startup errors."""
    try:
        from check_db import recommend_cosine, get_data_from_db
        from user_cf import predict_for_user, load_user_ratings
        import pandas as pd
        return recommend_cosine, get_data_from_db, pd, load_user_ratings, predict_for_user
    except ImportError as e:
        raise RuntimeError(f"Не удалось импортировать check_db, user_cf: {e}. Убедитесь, что файл scripts/check_db.py существует.")
    except Exception as e:
        raise RuntimeError(f"Ошибка при импорте check_db, user_cf: {e}")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL не задан. Укажите его в .env (формат: postgresql+psycopg2://...)?sslmode=require"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# Важно: autoincrement=True для ясности (в SQLAlchemy это поведение по умолчанию для PK Integer)
class Attraction(Base):
    __tablename__ = "attractions"   # схема public по умолчанию
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    city = Column(String, nullable=True)
    type = Column(String, nullable=True)
    transport = Column(String, nullable=True)
    price = Column(String, nullable=True)
    working_hours = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)

# Класс пользователя для аутентификации
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)

# Оценки пользователей
class Rating(Base):
    __tablename__ = "ratings"

    # композитный первичный ключ: один пользователь оценивает каждую достопримечательность максимум один раз
    user_id = Column(Integer, primary_key=True)
    attraction_id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)  # 1–5, ограничения есть на уровне DDL

# Планируемые к посещению достопримечательности
class PlannedVisit(Base):
    __tablename__ = "planned_visits"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    added_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

# Pydantic-схемы
class AttractionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название")

class AttractionRead(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    type: Optional[str] = None
    transport: Optional[str] = None
    price: Optional[str] = None
    working_hours: Optional[str] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    class Config:
        from_attributes = True  # Pydantic v2: ORM mode

# Recommendation models
class RecommendationRequest(BaseModel):
    city: Optional[str] = Field(None, description="Город")
    type: Optional[str] = Field(None, description="Тип достопримечательности")
    transport: Optional[str] = Field(None, description="Транспорт")
    price: Optional[str] = Field(None, description="Цена (Бесплатно/Платно)")
    desired_period: str = Field("anytime", description="Желаемое время (morning/afternoon/evening/night/anytime)")
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Минимальный рейтинг")
    top_k: int = Field(5, ge=1, le=50, description="Количество рекомендаций")

class RecommendationResult(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    type: Optional[str] = None
    transport: Optional[str] = None
    price: Optional[str] = None
    working_hours: Optional[str] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    score: float

# User authentication models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str

# User registration model
class RegisterRequest(BaseModel):
    username: str
    password: str

# Ratings input models
class RatingInput(BaseModel):
    attraction_id: int
    rating: int = Field(..., ge=1, le=5)


class RatingsBatchInput(BaseModel):
    user_id: int
    ratings: List[RatingInput]


class RatingsStatus(BaseModel):
    has_ratings: bool
    count: int

class PlannedVisitCreate(BaseModel):
    user_id: int
    attraction_id: int
    # дату с фронта НЕ требуем — используем now() в БД

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

app = FastAPI(title="Attractions Backend — базовые CRUD (auto-id)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Создаём таблицу, если её нет (безопасно).
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный логин или пароль",
        )

    token = secrets.token_hex(32)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )

@app.post("/auth/register", response_model=TokenResponse, summary="Регистрация пользователя")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # Проверяем, что такого username ещё нет
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует",
        )

    # Хэшируем пароль
    hashed = get_password_hash(data.password)

    user = User(
        username=data.username,
        hashed_password=hashed,
        is_admin=False,  # на всякий случай, не даём делать админов через этот эндпоинт
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать пользователя (ошибка уникальности)",
        )

    db.refresh(user)

    # После регистрации сразу «логиним» — отдаём токен
    token = secrets.token_hex(32)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )

@app.get(
    "/onboarding/attractions",
    response_model=List[AttractionRead],
    summary="Подборка достопримечательностей для первичной оценки",
)
def get_onboarding_attractions(limit: int = 15, db: Session = Depends(get_db)):
    """
    Возвращает случайные достопримечательности (по умолчанию 15 шт.)
    для экрана первичной оценки при регистрации.
    """
    stmt = (
        select(Attraction)
        .order_by(func.random())
        .limit(limit)
    )
    return db.scalars(stmt).all()

@app.post(
    "/planned-visits",
    status_code=status.HTTP_201_CREATED,
    summary="Добавить достопримечательность в список «Хочу посетить»",
)
def add_planned_visit(payload: PlannedVisitCreate, db: Session = Depends(get_db)):
    """
    Добавляет запись в public.planned_visits.
    Если такая пара (user_id, attraction_id) уже есть — делаем запрос идемпотентным
    и просто возвращаем статус `already_exists`.
    """
    # Проверим, что пользователь существует
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверим, что достопримечательность существует
    attraction = db.get(Attraction, payload.attraction_id)
    if not attraction:
        raise HTTPException(status_code=404, detail="Достопримечательность не найдена")

    # Композитный PK (user_id, attraction_id)
    existing = db.get(PlannedVisit, (payload.user_id, payload.attraction_id))
    if existing:
        return {
            "status": "already_exists",
            "user_id": payload.user_id,
            "attraction_id": payload.attraction_id,
            "added_at": existing.added_at,
        }

    visit = PlannedVisit(
        user_id=payload.user_id,
        attraction_id=payload.attraction_id,
        # added_at возьмётся из server_default=now() в БД
    )
    db.add(visit)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось добавить в список планов: {e}",
        )

    db.refresh(visit)

    return {
        "status": "created",
        "user_id": visit.user_id,
        "attraction_id": visit.attraction_id,
        "added_at": visit.added_at,
    }

@app.post(
    "/onboarding/ratings",
    status_code=status.HTTP_201_CREATED,
    summary="Сохранить первичные оценки пользователя",
)
def save_onboarding_ratings(payload: RatingsBatchInput, db: Session = Depends(get_db)):
    """
    Сохраняет/обновляет оценки пользователя для выбранных достопримечательностей.
    Используется после экрана с 15 объектами и звёздочками.
    """
    if not payload.ratings:
        raise HTTPException(status_code=400, detail="Список оценок пуст")

    # опционально можно проверить, что пользователь существует
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    try:
        for r in payload.ratings:
            # композитный PK: (user_id, attraction_id)
            pk = (payload.user_id, r.attraction_id)
            obj = db.get(Rating, pk)
            if obj:
                obj.rating = r.rating
            else:
                obj = Rating(
                    user_id=payload.user_id,
                    attraction_id=r.attraction_id,
                    rating=r.rating,
                )
                db.add(obj)

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении оценок: {e}")

    return {"status": "ok"}

@app.get(
    "/users/{user_id}/ratings-status",
    response_model=RatingsStatus,
    summary="Проверить, есть ли у пользователя оценки",
)
def get_ratings_status(user_id: int, db: Session = Depends(get_db)):
    """
    Возвращает, есть ли у пользователя хотя бы одна оценка, и их количество.
    """
    count = db.query(Rating).filter(Rating.user_id == user_id).count()
    return RatingsStatus(
        has_ratings=count > 0,
        count=count,
    )

@app.get("/test-recommendations")
def test_recommendations():
    """Test endpoint to check if check_db imports work."""
    try:
        _, get_data_from_db, _ = _import_recommendation_functions()
        df = get_data_from_db()
        return {
            "status": "ok",
            "columns": list(df.columns) if not df.empty else [],
            "row_count": len(df),
            "sample": df.head(2).to_dict('records') if not df.empty else []
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# ---------- БАЗОВЫЕ ЭНДПОИНТЫ ----------

@app.get("/attractions", response_model=List[AttractionRead], summary="Список записей")
def list_attractions(db: Session = Depends(get_db)):
    stmt = select(Attraction).order_by(Attraction.id)
    return db.scalars(stmt).all()

@app.get("/attractions/{attraction_id}", response_model=AttractionRead, summary="Получить по ID")
def get_attraction(attraction_id: int, db: Session = Depends(get_db)):
    obj = db.get(Attraction, attraction_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return obj

@app.post("/attractions", response_model=AttractionRead, status_code=status.HTTP_201_CREATED, summary="Создать запись")
def create_attraction(payload: AttractionCreate, db: Session = Depends(get_db)):
    obj = Attraction(name=payload.name)   # id сгенерируется БД
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при создании записи")
    db.refresh(obj)
    return obj

@app.delete("/attractions/{attraction_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить запись")
def delete_attraction(attraction_id: int, db: Session = Depends(get_db)):
    obj = db.get(Attraction, attraction_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.delete(obj)
    db.commit()
    return None

# ---------- РЕКОМЕНДАЦИИ ----------

@app.post("/recommendations", response_model=List[RecommendationResult], summary="Получить рекомендации")
def get_recommendations(request: RecommendationRequest):
    """Получить рекомендации на основе пользовательских предпочтений."""
    try:
        # Lazy import recommendation functions
        recommend_cosine, get_data_from_db, pd = _import_recommendation_functions()
        
        # Get data from database
        df = get_data_from_db()
        if df.empty:
            raise HTTPException(status_code=404, detail="База данных пуста")
        
        # Ensure required columns exist with defaults
        required_columns = [
            'id',
            'name',
            'city',
            'type',
            'transport',
            'price',
            'working_hours',
            'rating',
            'image_url',          
        ]
        for col in required_columns:
            if col not in df.columns:
                if col == 'id':
                    # If id doesn't exist, create it from index
                    df['id'] = df.index + 1
                elif col == 'rating':
                    df[col] = 0.0
                else:
                    df[col] = ''
        
        # Prepare user preferences
        user_prefs = {
            "desired_period": request.desired_period,
            "top_k": request.top_k
        }
        if request.city:
            user_prefs["city"] = request.city
        if request.type:
            user_prefs["type"] = request.type
        if request.transport:
            user_prefs["transport"] = request.transport
        if request.price:
            user_prefs["price"] = request.price
        if request.min_rating is not None:
            user_prefs["min_rating"] = request.min_rating
        
        # Get recommendations
        result_df = recommend_cosine(df, user_prefs, top_k=request.top_k)
        
        # Convert to list of dictionaries
        results = []
        for _, row in result_df.iterrows():
            # Safely extract values with proper null handling
            def safe_get(key, default=None):
                if key not in row:
                    return default
                val = row[key]
                if pd.isna(val):
                    return default
                return val
            
            results.append(RecommendationResult(
                id=int(safe_get('id', 0)),
                name=str(safe_get('name', '')),
                city=str(safe_get('city', '')) if safe_get('city') else None,
                type=str(safe_get('type', '')) if safe_get('type') else None,
                transport=str(safe_get('transport', '')) if safe_get('transport') else None,
                price=str(safe_get('price', '')) if safe_get('price') else None,
                working_hours=str(safe_get('working_hours', '')) if safe_get('working_hours') else None,
                rating=float(safe_get('rating', 0.0)) if safe_get('rating') is not None else None,
                image_url=str(safe_get('image_url', '')) if safe_get('image_url') else None,
                score=float(safe_get('score', 0.0)),   # 👈 ВАЖНО: добавили score
            ))
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Ошибка при получении рекомендаций: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console for debugging
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендаций: {str(e)}")
    
# ---------- USER-BASED RECOMMENDATIONS ЭНДПОИНТЫ ----------

@app.get(
    "/recommendations/user-based/{user_id}",
    response_model=List[RecommendationResult],
    summary="User-based Collaborative Filtering рекомендации"
)
def recommend_user_cf(user_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """
    User–User CF рекомендации на основе рейтингов других пользователей.
    """

    load_user_ratings, predict_for_user = _import_recommendation_functions()

    # 1. Загружаем данные
    user_ratings = load_user_ratings(db)

    if user_id not in user_ratings:
        raise HTTPException(status_code=404, detail="У пользователя нет оценок")

    # 2. Predict
    predictions = predict_for_user(user_id, user_ratings)

    if not predictions:
        return []

    # 3. Отсортируем по score
    ranked = sorted(
        predictions.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]

    # 4. Превращаем в объекты Attraction
    results = []
    for attr_id, score in ranked:
        attraction = db.get(Attraction, attr_id)
        if not attraction:
            continue

        results.append(
            RecommendationResult(
                id=attraction.id,
                name=attraction.name,
                city=attraction.city,
                type=attraction.type,
                transport=attraction.transport,
                price=attraction.price,
                working_hours=attraction.working_hours,
                rating=attraction.rating,
                image_url=attraction.image_url,
                score=float(score),
            )
        )

    return results