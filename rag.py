import os
import re
import json
import openai
from config import settings
from paquetes import PAQUETES

client = openai.Client(api_key=settings.OPENAI_API_KEY)

# ─────────────────────────────────────────────────────────────
# Catálogo completo — cargado una sola vez al arrancar
# ─────────────────────────────────────────────────────────────
_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conocimiento.md")

def _load_catalog() -> str:
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"No se pudo cargar el catalogo: {e}")
        return ""

CATALOG_COMPLETO = _load_catalog()
print(f"Catalogo cargado: {len(CATALOG_COMPLETO.splitlines())} lineas.")


# ─────────────────────────────────────────────────────────────
# Índice de precios en Python
# Los precios NUNCA vienen del LLM — se leen aquí directamente.
# ─────────────────────────────────────────────────────────────
def _parse_catalog_to_dict() -> dict:
    """
    Parsea conocimiento.md y devuelve:
      { "NOMBRE ESTUDIO": {precio_max, precio_min, muestra} }
    """
    catalog: dict = {}
    current_name: str | None = None
    current_data: dict = {}

    for line in CATALOG_COMPLETO.splitlines():
        if line.startswith("## "):
            if current_name:
                catalog[current_name] = current_data
            current_name = line[3:].strip()
            current_data = {"precio_max": 0.0, "precio_min": 0.0, "muestra": ""}
        elif current_name:
            if "PRECIO MÁXIMO SUGERIDO" in line:
                m = re.search(r'\$([0-9,]+(?:\.\d+)?)', line)
                if m:
                    current_data["precio_max"] = float(m.group(1).replace(",", ""))
            elif "PRECIO MÍNIMO SUGERIDO" in line:
                m = re.search(r'\$([0-9,]+(?:\.\d+)?)', line)
                if m:
                    current_data["precio_min"] = float(m.group(1).replace(",", ""))
            elif "Muestra requerida" in line:
                current_data["muestra"] = line.split(":", 1)[1].strip()

    if current_name:
        catalog[current_name] = current_data

    return catalog

CATALOG_DICT = _parse_catalog_to_dict()
print(f"Indice de precios: {len(CATALOG_DICT)} estudios cargados en Python.")


# ─────────────────────────────────────────────────────────────
# System prompt — construido UNA SOLA VEZ al arrancar.
# Mantenerlo constante es requisito para que OpenAI reutilice
# el prefijo cacheado y cobre solo el 50 % de esos tokens.
# ─────────────────────────────────────────────────────────────
_paquetes_txt = "\n".join(
    f"  - Paquete {num}: {p['nombre']} -> contiene: {', '.join(p['estudios'])}"
    for num, p in PAQUETES.items()
)

_SYS_PROMPT = f"""Eres el asistente de recepción del laboratorio OPLAB.
Tu única misión: identificar qué estudios clínicos pide el usuario y devolver
sus NOMBRES EXACTOS del catálogo. Los precios los maneja el sistema por su cuenta.

═══════════════════════════════════════════════
REGLAS (síguelas al pie de la letra):
═══════════════════════════════════════════════
0. REGLA ANTIALUCINACIÓN: SOLO puedes poner en "identificados" nombres que existan
   literalmente en el catálogo de abajo. Si no existe, va a "no_encontrados".
1. INFIERE inteligentemente: "AFP"→"ALFAFETOPROTEINA (AFP)", "estradiol"→"ESTRADIOL SERICO",
   "CA 15-3"→"CA-15-3", "LH"→"HORMONA LUTEINIZANTE", "FSH"→"HORMONA FOLICULO ESTIMULANTE".
2. PAQUETES: Si el usuario pide un paquete por número, expande TODOS sus estudios en "identificados".
   Si pide unir paquetes, suma estudios. Si pide excluir uno, quítalo.
   PAQUETES REGISTRADOS:
{_paquetes_txt}
3. SALUDOS / CONSULTA DE PAQUETES: Si el usuario saluda o pregunta por paquetes disponibles,
   responde en "mensaje" listando los paquetes con emojis y saltos de línea. "identificados" vacío.
4. AMBIGÜEDAD: si un nombre coincide con VARIOS estudios y no puedes elegir uno solo,
   agrégalo a "ambiguos".
5. NO ENCONTRADO: solo si el estudio no existe de ninguna forma en el catálogo.
6. Devuelve ÚNICAMENTE JSON válido, sin texto adicional.

═══════════════════════════════════════════════
ESTRUCTURA JSON A DEVOLVER:
═══════════════════════════════════════════════
{{
  "mensaje": "Respuesta amable al usuario. Si hay ambigüedad, pregunta. Si hay no encontrados, explica.",
  "identificados": ["NOMBRE EXACTO DEL CATÁLOGO", "OTRO NOMBRE EXACTO"],
  "ambiguos": [
    {{"solicitado": "como lo escribió el usuario", "opciones": ["OPCION A", "OPCION B"]}}
  ],
  "no_encontrados": ["nombre tal como lo escribió el usuario"]
}}

═══════════════════════════════════════════════
CATÁLOGO COMPLETO DE ESTUDIOS:
═══════════════════════════════════════════════
{CATALOG_COMPLETO}
"""
print(f"System prompt listo: {len(_SYS_PROMPT.split())} palabras aprox.")


# ─────────────────────────────────────────────────────────────
# Transcripción de audio (Whisper)
# ─────────────────────────────────────────────────────────────
def transcribe_audio(audio_path: str) -> str:
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="es"
        )
    return response.text.strip()


# ─────────────────────────────────────────────────────────────
# Motor de cotización
# GPT identifica nombres → Python busca precios en CATALOG_DICT
# ─────────────────────────────────────────────────────────────
def generate_rag_response(query: str) -> dict:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYS_PROMPT},
                {"role": "user",   "content": query}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        cached = getattr(response.usage, "prompt_tokens_cached", 0)
        if cached:
            print(f"Cache hit: {cached} tokens cacheados.")

        result = json.loads(response.choices[0].message.content)

        # Normalizar campos que GPT podría omitir
        identificados  = result.get("identificados", [])
        ambiguos       = result.get("ambiguos", [])
        no_encontrados = list(result.get("no_encontrados", []))

        # ── Lookup de precios en Python (nunca en el LLM) ────────
        cotizacion = []
        for nombre in identificados:
            entry = CATALOG_DICT.get(nombre)
            if entry and entry["precio_max"] > 0:
                cotizacion.append({
                    "estudio":       nombre,
                    "precio":        entry["precio_max"],
                    "precio_min":    entry["precio_min"],
                    "recomendacion": entry["muestra"],
                    "tiempo":        "2-8 horas",
                })
            else:
                # Nombre que GPT devolvió pero no existe en el índice
                no_encontrados.append(nombre)

        total     = sum(c["precio"]     for c in cotizacion)
        total_min = sum(c["precio_min"] for c in cotizacion)
        genera_pdf = bool(cotizacion and not ambiguos and not no_encontrados)

        return {
            "mensaje":        result.get("mensaje", ""),
            "genera_pdf":     genera_pdf,
            "cotizacion":     cotizacion,
            "ambiguos":       ambiguos,
            "no_encontrados": no_encontrados,
            "total":          total,
            "total_min":      total_min,
        }

    except Exception as e:
        print("Error en generate_rag_response:", e)
        return {
            "mensaje":        "Hubo un error procesando tu solicitud. Intenta de nuevo.",
            "genera_pdf":     False,
            "cotizacion":     [],
            "ambiguos":       [],
            "no_encontrados": [],
            "total":          0,
            "total_min":      0,
        }
