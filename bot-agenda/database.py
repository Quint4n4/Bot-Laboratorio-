"""
database.py - Modelos y configuración de la base de datos SQLite
Agenda Bot - Asistente Personal
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String,
    DateTime, Boolean, Text, Enum
)
from sqlalchemy.orm import declarative_base, sessionmaker
import enum
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'agenda.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EventType(str, enum.Enum):
    reminder = "reminder"   # Recordatorio puntual (en X minutos)
    meeting   = "meeting"   # Cita o reunión con hora de fin
    task      = "task"      # Tarea sin hora exacta, solo fecha


class EventStatus(str, enum.Enum):
    pending   = "pending"
    completed = "completed"
    cancelled = "cancelled"
    snoozed   = "snoozed"


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    telegram_id      = Column(String, unique=True, nullable=False, index=True)
    full_name        = Column(String, nullable=True)
    timezone         = Column(String, default="America/Mexico_City")
    voice_persona    = Column(String, default="nova")   # Nova, Shimmer, Onyx, Alloy, Echo, Fable
    morning_hour     = Column(Integer, default=8)       # Hora del briefing matutino
    evening_hour     = Column(Integer, default=20)      # Hora del wrap-up nocturno
    voice_replies    = Column(Boolean, default=True)    # Si el bot responde con voz
    created_at       = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id               = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, nullable=False, index=True)
    title            = Column(String, nullable=False)
    description      = Column(Text, nullable=True)
    event_type       = Column(String, default=EventType.reminder)
    status           = Column(String, default=EventStatus.pending)
    start_datetime   = Column(DateTime, nullable=False)
    end_datetime     = Column(DateTime, nullable=True)    # Para citas/reuniones
    all_day          = Column(Boolean, default=False)     # Evento de todo el día
    reminder_sent    = Column(Boolean, default=False)
    last_reminded_at = Column(DateTime, nullable=True)   # Para follow-ups
    followup_count   = Column(Integer, default=0)        # Cuántas veces se ha insistido
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Crea todas las tablas si no existen."""
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente (agenda.db).")


def get_db():
    """Generador de sesión para usar en cada operación."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
