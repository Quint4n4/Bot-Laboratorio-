import re

def sort_cortisol():
    with open("c:\\whatsap-bot\\conocimiento.md", "r", encoding="utf-8") as f:
        content = f.read()

    # The block might look like:
    # ## CORTISOL
    # - PRECIO MÁXIMO SUGERIDO: $500
    # - PRECIO MÍNIMO SUGERIDO: $300
    # - Muestra requerida: Suero Tubo rojo o amarillo
    
    # Extraemos el bloque del final
    cortisol_pattern = re.compile(r'(\n)?(?:## CORTISOL\n- PRECIO MÁXIMO SUGERIDO: \$500\n- PRECIO MÍNIMO SUGERIDO: \$300\n- Muestra requerida: Suero Tubo rojo o amarillo\n?)')
    
    match = cortisol_pattern.search(content)
    if not match:
        print("Bloque de cortisol no encontrado exactamente, intentando busqueda mas amplia.")
        cortisol_pattern = re.compile(r'(\n)?## CORTISOL[\s\S]*?(?=\n## |\Z)')
        match = cortisol_pattern.search(content)
        if not match:
            print("No se encontró el bloque de cortisol en absoluto.")
            return
            
    cortisol_block = match.group(0).strip()
    
    # Eliminamos el bloque original
    content = content[:match.start()] + content[match.end():]
    
    # Ahora buscamos el punto de insersión alfabéticamente.
    # Buscamos la posición donde haya un header ## C... que vaya después de CORTISOL
    # o el último header antes de él.
    
    headers = list(re.finditer(r'^## ([A-Za-z0-9\.\-\s]+)', content, flags=re.MULTILINE))
    
    insert_pos = -1
    
    for i, h in enumerate(headers):
        title = h.group(1).strip().upper()
        if title > "CORTISOL":
            insert_pos = h.start()
            break
            
    if insert_pos == -1:
        # Se queda al final
        insert_pos = len(content)
        
    final_content = content[:insert_pos] + "\n## CORTISOL\n- PRECIO MÁXIMO SUGERIDO: $500\n- PRECIO MÍNIMO SUGERIDO: $300\n- Muestra requerida: Suero Tubo rojo o amarillo\n\n" + content[insert_pos:]
    
    with open("c:\\whatsap-bot\\conocimiento.md", "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print("Cortisol movido exitosamente al orden alfabetico.")

if __name__ == '__main__':
    sort_cortisol()
