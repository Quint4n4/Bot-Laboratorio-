"""
config.py
---------
Carga y valida todas las variables de entorno del proyecto.
Importa desde aquí para acceder a las constantes tipadas en cualquier módulo.

Uso:
    from config import settings
    print(settings.SUPABASE_URL)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
import os

# Carga el .env desde la raíz del proyecto
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _require(key: str) -> str:
    """Lee una variable de entorno; falla rápido si está vacía."""
    value = os.getenv(key, "").strip()
    if not value:
        print(f"❌  Variable de entorno requerida no configurada: {key}")
        print(f"    → Edita el archivo .env y asigna un valor a {key}")
        sys.exit(1)
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ─── Supabase ─────────────────────────────────────────────────────────────────
class _Settings:
    # Supabase
    SUPABASE_URL:   Final[str] = _require("SUPABASE_URL")
    SUPABASE_KEY:   Final[str] = _require("SUPABASE_KEY")

    # OpenAI
    OPENAI_API_KEY: Final[str] = _require("OPENAI_API_KEY")

    # Telegram
    TELEGRAM_BOT_TOKEN: Final[str] = _require("TELEGRAM_BOT_TOKEN") 

    # Modelo de embeddings (compatible con la columna vector(1536) de la DB)
    EMBEDDING_MODEL: Final[str] = _optional("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMS:  Final[int] = 1536

    # Parámetros RAG
    MATCH_THRESHOLD: Final[float] = float(_optional("MATCH_THRESHOLD", "0.50"))
    MATCH_COUNT:     Final[int]   = int(_optional("MATCH_COUNT", "10"))

    # Evolution API / WhatsApp
    EVOLUTION_API_URL: Final[str] = _optional("EVOLUTION_API_URL", "http://localhost:8080")
    EVOLUTION_API_KEY: Final[str] = _optional("EVOLUTION_API_KEY", "secret_123")
    INSTANCE_NAME:     Final[str] = _optional("INSTANCE_NAME", "dev_instance")


settings = _Settings()
