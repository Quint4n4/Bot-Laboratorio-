import os
import json
import openai
from database import supabase
from config import settings

# Inicializar cliente de OpenAI
client = openai.Client(api_key=settings.OPENAI_API_KEY)

# ─────────────────────────────────────────────────────────────
# Catálogo completo cargado una sola vez al arrancar
# ─────────────────────────────────────────────────────────────
_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conocimiento.md")

def _load_catalog() -> str:
    """Carga el catálogo completo desde conocimiento.md."""
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ No se pudo cargar el catálogo: {e}")
        return ""

# Cargamos una vez al inicio (no en cada request)
CATALOG_COMPLETO = _load_catalog()
print(f"📚 Catálogo cargado: {len(CATALOG_COMPLETO.splitlines())} líneas.")

# ─────────────────────────────────────────────────────────────
# Embeddings (para ingestión, no para búsqueda de cotización)
# ─────────────────────────────────────────────────────────────
def get_embedding(text: str) -> list[float]:
    """Genera un vector para ingestión en Supabase."""
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=settings.EMBEDDING_MODEL)
    return response.data[0].embedding

# ─────────────────────────────────────────────────────────────
# Transcripción de audio (Whisper)
# ─────────────────────────────────────────────────────────────
def transcribe_audio(audio_path: str) -> str:
    """Transcribe un archivo de audio usando OpenAI Whisper."""
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="es"
        )
    return response.text.strip()

from paquetes import PAQUETES

# ─────────────────────────────────────────────────────────────
# Motor principal de cotización (catálogo completo en prompt)
# ─────────────────────────────────────────────────────────────
def generate_rag_response(query: str) -> dict:
    """
    Envía el CATÁLOGO COMPLETO al prompt de GPT para que haga matching
    fuzzy/inteligente sin depender de búsqueda vectorial.
    GPT infiere el estudio correcto aunque el usuario no escriba el nombre exacto.
    """
    
    # Preparamos la descripción literal de los paquetes para que la IA sepa restarlos o sumarlos
    paquetes_txt = "\n".join(
        f"  - Paquete {num}: {p['nombre']} -> contiene: {', '.join(p['estudios'])}"
        for num, p in PAQUETES.items()
    )

    sys_prompt = f"""Eres el mejor asistente virtual de recepción del laboratorio OPLAB.
Tu misión: identificar qué estudios clínicos pide el usuario, encontrarlos en el catálogo
(aunque el nombre no sea exacto), extraer sus PRECIO MÁXIMO SUGERIDO y armar la cotización.

═══════════════════════════════════════════════
REGLAS DE BÚSQUEDA (críticas — síguelas al pie de la letra):
═══════════════════════════════════════════════
1. INFIERE inteligentemente: "AFP"→"ALFAFETOPROTEINA (AFP)", "estradiol"→"ESTRADIOL SERICO",
   "CA 15-3"→"CA-15-3", "LH"→"HORMONA LUTEINIZANTE", "FSH"→"HORMONA FOLICULO ESTIMULANTE".
   Si puedes deducirlo con certeza, ponlo directamente en "cotizacion".
2. PAQUETES DE ESTUDIOS: El usuario puede solicitar paquetes enteros por número (ej: "1", "paquete 1").
   Si pide un paquete, despliega e inserta TODOS los estudios correspondientes en "cotizacion".
   MUY IMPORTANTE: Si pide UNIR varios paquetes (ej: "paquete 1 y 2"), suma todos sus estudios.
   Si pide ELIMINAR (ej: "paquete 1 pero sin glucosa"), excluye la glucosa de la lista final.
   Si pide AGREGAR (ej: "paquete 1 más perfil tiroideo"), suma ambos.
   
   ⚠️ DEFAULT Y SALUDOS: Si el usuario te SALUDA de forma genérica ("hola", "buenos días") o 
   TE PREGUNTA por los paquetes disponibles ("¿qué paquetes hay?"), tú debes responderle en el 
   campo "mensaje" listando los paquetes de manera HERMOSA, AGRUPADA Y BIEN ORDENADA. 
   Usa OBLIGATORIAMENTE un salto de línea (\\n) para cada paquete y sus emojis correspondientes.
   Ejemplo de cómo debes formatearlo en el mensaje:
   "¡Hola! Tenemos estos paquetes predefinidos:\\n\\n🔵 *Paquete 1:* Check-up General\\n🟢 *Paquete 2:* Metabólico..."
   
   PAQUETES REGISTRADOS QUE DEBES REPORTAR O PROCESAR:
{paquetes_txt}
3. AMBIGÜEDAD (campo "ambiguos"): si el nombre del usuario coincide con VARIOS estudios
   del catálogo y NO puedes elegir uno solo, agrégalo al arreglo "ambiguos".
4. NO ENCONTRADO (campo "no_encontrados"): solo cuando el estudio no exista de ninguna
   forma en el catálogo ni en los paquetes.
5. Usa SIEMPRE el campo "PRECIO MÁXIMO SUGERIDO" de cada estudio como precio.
6. "genera_pdf": true solo cuando TODO en "cotizacion" está resuelto Y "ambiguos" está vacío.
7. Devuelve ÚNICAMENTE un JSON válido, sin texto adicional.

═══════════════════════════════════════════════
ESTRUCTURA JSON A DEVOLVER:
═══════════════════════════════════════════════
{{
  "mensaje": "Respuesta amable. Si hay ambigüedad, pregunta cuál estudio elige. Si hay no encontrados, explica cuál.",
  "genera_pdf": true,
  "cotizacion": [
    {{"estudio": "NOMBRE EXACTO DEL CATÁLOGO", "precio": 215, "recomendacion": "Muestra requerida", "tiempo": "2-8 hrs"}}
  ],
  "ambiguos": [
    {{"solicitado": "nombre como lo escribió el usuario", "opciones": ["OPCION A DEL CATÁLOGO", "OPCION B DEL CATÁLOGO"]}}
  ],
  "no_encontrados": ["nombre tal como lo escribió el usuario, si no existe en absoluto"],
  "total": 215
}}

═══════════════════════════════════════════════
CATÁLOGO COMPLETO DE ESTUDIOS Y PRECIOS:
═══════════════════════════════════════════════
{CATALOG_COMPLETO}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        # Garantizar que todos los campos siempre existan
        if "no_encontrados" not in result:
            result["no_encontrados"] = []
        if "ambiguos" not in result:
            result["ambiguos"] = []
        if "cotizacion" not in result:
            result["cotizacion"] = []
        return result

    except Exception as e:
        print("Error decodificando JSON de OpenAI:", e)
        return {
            "mensaje": "Hubo un error procesando tu solicitud. Intenta de nuevo.",
            "genera_pdf": False,
            "cotizacion": [],
            "ambiguos": [],
            "no_encontrados": [],
            "total": 0
        }
