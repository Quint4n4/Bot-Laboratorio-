"""
db.py — Conexión a Postgres compartida con el bot ARIA.
Usa los mismos modelos para que dashboard y bot estén sincronizados.
"""
import os
from sqlalchemy import (
    create_engine, Column, Integer, String,
    DateTime, Boolean, Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DB_URL_REAL", "").strip().strip('"').strip("'")
if not DATABASE_URL:
    raise RuntimeError("DB_URL_REAL no configurado")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    telegram_id   = Column(String, unique=True, nullable=False)
    full_name     = Column(String, nullable=True)
    timezone      = Column(String, default="America/Mexico_City")
    voice_persona = Column(String, default="nova")


class Event(Base):
    __tablename__ = "events"
    id               = Column(Integer, primary_key=True)
    user_telegram_id = Column(String, nullable=False)
    title            = Column(String, nullable=False)
    description      = Column(Text, nullable=True)
    event_type       = Column(String)
    status           = Column(String)
    start_datetime   = Column(DateTime, nullable=False)
    end_datetime     = Column(DateTime, nullable=True)
    all_day          = Column(Boolean, default=False)
    location         = Column(String, nullable=True)
    recurrence_rule  = Column(String, nullable=True)
    attendees        = Column(Text, nullable=True)
    tags             = Column(String, nullable=True)
    category         = Column(String, default="otros")
    created_at       = Column(DateTime)
    updated_at       = Column(DateTime)


class Message(Base):
    __tablename__ = "messages"
    id               = Column(Integer, primary_key=True)
    user_telegram_id = Column(String, nullable=False)
    role             = Column(String, nullable=False)
    content          = Column(Text, nullable=False)
    created_at       = Column(DateTime)
