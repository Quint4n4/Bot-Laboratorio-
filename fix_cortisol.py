import re

def fix_cortisol():
    with open("c:\\whatsap-bot\\conocimiento.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Eliminar cualquier rastro malformado si lo hay (por si acaso)
    content = re.sub(r'(\n)?## CORTISOL[\s\S]*?(?=\n## |\Z)', '', content)
    
    headers = list(re.finditer(r'^## ([A-Za-z0-9\.\-\s]+)', content, flags=re.MULTILINE))
    
    insert_pos = len(content)
    # Encontrar la "C" correspondiente
    for h in headers:
        title = h.group(1).strip().upper()
        if title > "CORTISOL":
            insert_pos = h.start()
            break
            
    cortisol_entry = """
## CORTISOL
- PRECIO MÁXIMO SUGERIDO: $500
- PRECIO MÍNIMO SUGERIDO: $300
- Muestra requerida: Suero Tubo rojo o amarillo

"""
    final_content = content[:insert_pos] + cortisol_entry + content[insert_pos:]
    
    with open("c:\\whatsap-bot\\conocimiento.md", "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print("Cortisol regenerado en la posicion correcta.")

if __name__ == '__main__':
    fix_cortisol()
