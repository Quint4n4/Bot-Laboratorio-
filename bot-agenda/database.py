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
# Se exige la variable DB_URL_REAL explícita para evitar colisiones en Railway
DATABASE_URL = os.getenv("DB_URL_REAL")

if not DATABASE_URL:
    raise ValueError("❌ ERROR FATAL: No se encontró la variable de entorno 'DB_URL_REAL'. ¡Configúrala en Railway apuntando a tu PostgreSQL!")

# Configuración del engine (check_same_thread es solo para SQLite)
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
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

    # Campos enriquecidos (v2)
    location         = Column(String,  nullable=True)     # Dirección o link de Zoom/Meet
    recurrence_rule  = Column(String,  nullable=True)     # "daily" | "weekly:MO,WE" | "monthly:15"
    attendees        = Column(Text,    nullable=True)     # CSV de nombres / emails
    tags             = Column(String,  nullable=True)     # CSV libre: "proyecto-alpha,urgente"
    category         = Column(String,  default="otros")   # personal|trabajo|salud|finanzas|familia|social|otros

    reminder_sent    = Column(Boolean, default=False)
    last_reminded_at = Column(DateTime, nullable=True)   # Para follow-ups
    followup_count   = Column(Integer, default=0)        # Cuántas veces se ha insistido
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    """Historial conversacional por usuario para memoria multi-turno de ARIA."""
    __tablename__ = "messages"

    id               = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, nullable=False, index=True)
    role             = Column(String, nullable=False)   # 'user' | 'assistant'
    content          = Column(Text,   nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow, index=True)


def _migrate_event_columns():
    """
    Agrega columnas nuevas a events si la tabla ya existia.
    SQLAlchemy.create_all NO modifica tablas existentes; solo crea las que faltan.
    Este migrator es idempotente: usa ADD COLUMN IF NOT EXISTS (Postgres 9.6+).
    """
    cols_to_add = [
        ("location",        "VARCHAR"),
        ("recurrence_rule", "VARCHAR"),
        ("attendees",       "TEXT"),
        ("tags",            "VARCHAR"),
        ("category",        "VARCHAR DEFAULT 'otros'"),
    ]

    if "sqlite" in DATABASE_URL:
        # SQLite: usar PRAGMA + ALTER TABLE manual (no soporta IF NOT EXISTS)
        with engine.begin() as conn:
            from sqlalchemy import text
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(events)")).fetchall()}
            for col_name, col_def in cols_to_add:
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE events ADD COLUMN {col_name} {col_def}"))
        return

    # Postgres
    with engine.begin() as conn:
        from sqlalchemy import text
        for col_name, col_def in cols_to_add:
            conn.execute(text(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {col_name} {col_def}"))


def init_db():
    """Crea todas las tablas si no existen y migra columnas nuevas en events."""
    Base.metadata.create_all(bind=engine)
    _migrate_event_columns()
    print("✅ Base de datos inicializada correctamente (agenda.db).")


def get_db():
    """Generador de sesión para usar en cada operación."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
