"""
voice_handler.py - Entrada y salida de voz
Agenda Bot - Asistente Personal
Usa ElevenLabs para TTS con calidad de actor de doblaje en español.
"""
import os
import re
import tempfile

from openai import OpenAI

# ElevenLabs
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

# ---------------------------------------------------------------------------
# Clientes de API
# ---------------------------------------------------------------------------
_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", ""))

# ---------------------------------------------------------------------------
# Voces de ElevenLabs curadas para español (nombre → voice_id)
# Puedes agregar más desde: https://elevenlabs.io/app/voice-library
# ---------------------------------------------------------------------------
ELEVENLABS_VOICES = {
    # Voces femeninas
    "aria":    "9BWtsMINqrJLrRacOk9x",   # Aria — Natural, expresiva (recomendada)
    "sarah":   "EXAVITQu4vr4xnSDxMaL",   # Sarah — Suave y clara
    "laura":   "FGY2WhTYpPnrIDTdsKH5",   # Laura — Joven y amigable
    "paula":   "pFZP5JQG7iQjIQuC4Bku",   # Paula — Cálida y profesional
    # Voces masculinas
    "river":   "SAz9YHcvj6GT2YYXdXww",   # River — Neutral y claro
    "charlie": "IKne3meq5aSn9XLyUdCD",   # Charlie — Casual
    "liam":    "TX3LPaxmHKxFdv7VOQHJ",   # Liam — Joven y energético
    "eric":    "cjVigY5qzO86Huf0OWal",   # Eric — Profesional
}

# Voz por defecto
DEFAULT_ELEVEN_VOICE = "aria"

# Modelo Turbo v2.5: soporta language_code para forzar español sin importar
# la longitud del texto. Esto evita el bug del v2 multilingüe que cambiaba
# a inglés en frases cortas (<25 chars).
ELEVEN_MODEL = "eleven_turbo_v2_5"
ELEVEN_LANGUAGE = "es"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _clean_for_tts(text: str) -> str:
    """
    Limpia el texto para que suene natural:
    - Elimina formato Markdown (* _ ` #)
    - Elimina emojis
    - Asegura que termine en puntuación para no cortar el audio
    """
    # Quitar formato Markdown
    text = re.sub(r"[*_`#~]", "", text)
    # Quitar comandos tipo /start
    text = re.sub(r"/\w+", "", text)
    # Reemplazar guiones por coma (pausa natural)
    text = text.replace("—", ",").replace("--", ",")
    # Eliminar emojis Unicode
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]", "", text)
    # Limpiar espacios múltiples
    text = re.sub(r" {2,}", " ", text).strip()
    # Asegurar puntuación al final para evitar que el audio se corte
    if text and text[-1] not in ".!?,;:":
        text += "."
    return text


def get_eleven_voice_id(voice_name: str) -> str:
    """Retorna el voice_id de ElevenLabs dado un nombre de voz."""
    return ELEVENLABS_VOICES.get(voice_name.lower(), ELEVENLABS_VOICES[DEFAULT_ELEVEN_VOICE])


# ---------------------------------------------------------------------------
# STT: Transcripción de notas de voz con Whisper (OpenAI)
# ---------------------------------------------------------------------------
async def transcribe_voice(file_path: str) -> str:
    """
    Transcribe un archivo de audio usando OpenAI Whisper.
    Se ejecuta en un executor para no bloquear el event loop.
    """
    def _transcribe():
        with open(file_path, "rb") as f:
            response = _openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es",
                response_format="text"
            )
        return response

    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe)


# ---------------------------------------------------------------------------
# TTS: Síntesis de voz con ElevenLabs
# ---------------------------------------------------------------------------
async def text_to_speech(text: str, voice: str = DEFAULT_ELEVEN_VOICE) -> str:
    """
    Convierte texto a audio MP3 usando ElevenLabs Turbo v2.5 con español forzado.
    Garantiza voz consistente (Aria u otra elegida) sin importar la longitud
    del texto. Solo se cae a OpenAI TTS si ElevenLabs API está completamente caído.
    """
    cleaned = _clean_for_tts(text)
    voice_id = get_eleven_voice_id(voice)

    def _call_elevenlabs():
        audio_generator = _eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=cleaned,
            model_id=ELEVEN_MODEL,
            language_code=ELEVEN_LANGUAGE,   # Fuerza español incluso en texto corto
            voice_settings=VoiceSettings(
                stability=0.50,
                similarity_boost=0.85,
                style=0.30,
                use_speaker_boost=True,
            ),
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        for chunk in audio_generator:
            tmp.write(chunk)
        tmp.close()
        return tmp.name

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call_elevenlabs)
    except Exception as e:
        print(f"[TTS] ElevenLabs falló, fallback a OpenAI. Motivo: {e}")
        # Fallback solo si ElevenLabs está completamente abajo. Idealmente nunca pasa.
        response = _openai_client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=cleaned,
            speed=0.95,
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(response.content)
        tmp.close()
        return tmp.name

