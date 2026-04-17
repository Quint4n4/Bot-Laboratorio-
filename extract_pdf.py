import re
import pdfplumber

def main():
    print("Leyendo el archivo PDF...")
    text_blocks = []
    
    with pdfplumber.open("LISTA DE PRECIOS MAQUILA OPLAB 2026.pdf") as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_blocks.append(text)
                
    raw_text = "\n".join(text_blocks)
    _regenerar_conocimiento(raw_text)

def regenerar_desde_conocimiento():
    """Versión alternativa: lee el conocimiento.md actual (ya extraído) y lo reformatea."""
    with open("conocimiento.md", "r", encoding="utf-8") as f:
        raw_text = f.read()
    _regenerar_conocimiento(raw_text)

def _regenerar_conocimiento(raw_text: str):
    # La estructura de cada fila tiene 4 precios seguidos de muestra/tiempo.
    # Los 4 precios son: MINIMO | SIN IVA | CON IVA* | PRECIO MAXIMO SUGERIDO
    # Queremos la 4ta columna (PRECIO MÁXIMO SUGERIDO).
    patron = re.compile(
        r'(\d{1,3})\s+\S+\s+([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ0-9 \.,\(\)\-\/]+?)\s+'  # num clave nombre
        r'\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)\s+'  # 4 precios
        r'(.+?)\s+(?:\d+-\d+\s+(?:dias?|hrs?))',   # muestra + tiempo
        re.IGNORECASE
    )

    markdown = "# Catálogo Oficial de Estudios Clínicos OPLAB 2026\n\n"
    markdown += "INSTRUCCIÓN IMPORTANTE: Usa SIEMPRE el campo 'PRECIO MÁXIMO SUGERIDO' para cotizar. No uses ningún otro precio.\n\n"
    markdown += "---\n\n"

    matches_found = 0
    for m in patron.finditer(raw_text):
        nombre = m.group(2).strip()
        precio_max = m.group(6).replace(",", "")
        muestra = m.group(7).strip()

        markdown += f"## {nombre}\n"
        markdown += f"- PRECIO MÁXIMO SUGERIDO: ${precio_max}\n"
        markdown += f"- Muestra requerida: {muestra}\n\n"
        matches_found += 1

    if matches_found < 50:
        print(f"⚠️  Solo se reconocieron {matches_found} estudios. Añadiendo texto raw como respaldo...")
        markdown += "\n\n---\n## TEXTO COMPLETO DE REFERENCIA (respaldo)\n\n"
        markdown += raw_text

    markdown += "\n\n---\n## RECOMENDACIONES PREVIAS Y PREPARACIÓN\n\n"
    markdown += """1. AYUNO (Química Sanguínea, Glucosa, Perfil de Lípidos, etc.):
- Ayuno estricto de 8 a 12 horas. Solo agua pura.

2. ORINA (Examen General de Orina, Urocultivo, etc.):
- Primera orina de la mañana, aseo íntimo previo, frasco estéril, chorro medio.

3. HECES (Coprocultivo, Coproparasitoscópico, Sangre Oculta):
- Muestra tamaño nuez en frasco estéril, sin contacto con agua del inodoro u orina.

4. ESPERMA (Espermatobioscopia):
- Abstinencia sexual 3-5 días, muestra completa por masturbación en frasco estéril, entregar antes de 45 min.

5. EXUDADOS (Faríngeo, Vaginal, Uretral, etc.):
- No antibióticos (3 días mínimo). Faríngeo: ayuno sin lavado de dientes.
- Vaginal: sin relaciones 48h, sin lavados ni óvulos, fuera de periodo menstrual.
"""

    with open("conocimiento.md", "w", encoding="utf-8") as f:
        f.write(markdown)
        
    print(f"✅ conocimiento.md regenerado con éxito. Estudios catalogados: {matches_found}")

if __name__ == "__main__":
    # Usar la versión desde conocimiento.md (sin releer el PDF lento)
    regenerar_desde_conocimiento()
