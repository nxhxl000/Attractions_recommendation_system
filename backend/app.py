# backend/app.py
import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from dotenv import load_dotenv
load_dotenv()

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

# Pydantic-схемы
class AttractionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название")

class AttractionRead(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True  # Pydantic v2: ORM mode

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