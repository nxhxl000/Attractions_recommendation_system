# backend/app.py
import os
import sys
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

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
        import pandas as pd
        return recommend_cosine, get_data_from_db, pd
    except ImportError as e:
        raise RuntimeError(f"Не удалось импортировать check_db: {e}. Убедитесь, что файл scripts/check_db.py существует.")
    except Exception as e:
        raise RuntimeError(f"Ошибка при импорте check_db: {e}")

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
    score: float

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        required_columns = ['id', 'name', 'city', 'type', 'transport', 'price', 'working_hours', 'rating']
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
                score=float(safe_get('score', 0.0))
            ))
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Ошибка при получении рекомендаций: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console for debugging
        raise HTTPException(status_code=500, detail=f"Ошибка при получении рекомендаций: {str(e)}")