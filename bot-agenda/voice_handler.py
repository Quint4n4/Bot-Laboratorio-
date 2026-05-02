"""
voice_handler.py - Entrada y salida de voz
Agenda Bot - Asistente Personal
Usa OpenAI Whisper para STT y OpenAI TTS-1-HD para sintesis de voz consistente.
"""
import logging
import os
import re
import tempfile

from openai import OpenAI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cliente OpenAI
# Strip defensivo de la API key para prevenir saltos de linea o comillas
# accidentales pegados en variables de entorno (Railway/Heroku/etc).
# ---------------------------------------------------------------------------
def _clean_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip('"').strip("'")


_openai_client = OpenAI(api_key=_clean_env("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# Voces de OpenAI (todas funcionan en español)
# ---------------------------------------------------------------------------
OPENAI_VOICES = {
    "nova":    "Nova — Femenina, clara (recomendada) 🌟",
    "shimmer": "Shimmer — Femenina, suave",
    "alloy":   "Alloy — Neutral",
    "echo":    "Echo — Masculina, calma",
    "fable":   "Fable — Masculina, expresiva",
    "onyx":    "Onyx — Masculina, profunda",
}

DEFAULT_VOICE = "nova"
TTS_MODEL = "tts-1-hd"   # Alta calidad
TTS_SPEED = 0.95         # Ligeramente lento para sonar natural en español


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _clean_for_tts(text: str) -> str:
    """
    Limpia el texto para que suene natural:
    - Elimina formato Markdown (* _ ` #)
    - Elimina emojis
    - Normaliza guiones largos a comas (pausa)
    - Asegura que termine en puntuación
    """
    text = re.sub(r"[*_`#~]", "", text)
    text = re.sub(r"/\w+", "", text)
    text = text.replace("—", ",").replace("--", ",")
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-⛿✀-➿]", "", text)
    text = re.sub(r" {2,}", " ", text).strip()
    if text and text[-1] not in ".!?,;:":
        text += "."
    return text


def _resolve_voice(voice: str) -> str:
    """
    Devuelve un voice válido de OpenAI. Si el usuario tiene un valor antiguo
    (ej. 'aria' de cuando se usaba ElevenLabs) usa el default.
    """
    return voice if voice in OPENAI_VOICES else DEFAULT_VOICE


# ---------------------------------------------------------------------------
# STT: Transcripción de notas de voz (Whisper)
# ---------------------------------------------------------------------------
async def transcribe_voice(file_path: str) -> str:
    """Transcribe un archivo de audio a texto con Whisper."""
    def _transcribe():
        with open(file_path, "rb") as f:
            response = _openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es",
                response_format="text",
            )
        return response

    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe)


# ---------------------------------------------------------------------------
# TTS: Síntesis de voz con OpenAI
# ---------------------------------------------------------------------------
async def text_to_speech(text: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Convierte texto a audio MP3 con OpenAI TTS-1-HD.
    Voz 100% consistente sin importar la longitud del texto (no hay fallback
    a otros providers — siempre usa OpenAI).
    """
    cleaned = _clean_for_tts(text)
    chosen_voice = _resolve_voice(voice)

    def _call_openai():
        response = _openai_client.audio.speech.create(
            model=TTS_MODEL,
            voice=chosen_voice,
            input=cleaned,
            speed=TTS_SPEED,
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(response.content)
        tmp.close()
        return tmp.name

    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_openai)
