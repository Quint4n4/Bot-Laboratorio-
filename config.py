"""
config.py
---------
Carga y valida todas las variables de entorno del proyecto.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
import os

_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        print(f"❌  Variable de entorno requerida no configurada: {key}")
        print(f"    → Edita el archivo .env y asigna un valor a {key}")
        sys.exit(1)
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


class _Settings:
    OPENAI_API_KEY:     Final[str] = _require("OPENAI_API_KEY")
    TELEGRAM_BOT_TOKEN: Final[str] = _require("TELEGRAM_BOT_TOKEN")
    DATABASE_URL:       Final[str] = _optional("DATABASE_URL")


settings = _Settings()
