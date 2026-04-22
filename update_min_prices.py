import re
import difflib
from pypdf import PdfReader

def extract_pdf_prices(pdf_path="LISTA DE PRECIOS MAQUILA OPLAB 2026.pdf"):
    r = PdfReader(pdf_path)
    text = ""
    for p in r.pages:
        text += p.extract_text() + "\n"
        
    pricemap = {}
    # Busca 2 a 4 precios seguidos como $320.00 $371 $483 $724
    pattern = re.compile(r'([A-Za-z0-9\.\-\s\(\)\/\+]+)\$([0-9\.,]+)(?:\s*\$([0-9\.,]+))?')
    
    for line in text.split("\n"):
        # limpiar basura de espacios extra
        match = pattern.search(line)
        if match:
            # Quitamos los numeros ID del inicio buscando el primer espacio o quitando numeros
            raw_name = match.group(1).strip()
            # remueve codigos numericos "10 AMI..." -> "AMILASA"
            parts = raw_name.split()
            if len(parts) > 2 and parts[0].isdigit():
                raw_name = " ".join(parts[2:]) # Quita ID y abreviación
            
            if len(raw_name) > 3 and not raw_name.upper().startswith("PRECIO"):
                precio_str = match.group(2).replace(",", "")
                precio_min = float(precio_str)
                pricemap[raw_name.upper()] = precio_min
                
    return pricemap

def update_conocimiento():
    pricemap = extract_pdf_prices()
    
    with open("conocimiento.md", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    current_study = None
    
    for line in lines:
        if line.startswith("## "):
            current_study = line[3:].strip().upper()
            new_lines.append(line)
            continue
            
        new_lines.append(line)
        
        if line.startswith("- PRECIO MÁXIMO SUGERIDO:"):
            # Buscar el estudio más parecido
            if current_study == "DHES":
                new_lines.append("- PRECIO MÍNIMO SUGERIDO: $300\n")
            elif current_study:
                matches = difflib.get_close_matches(current_study, pricemap.keys(), n=1, cutoff=0.6)
                if matches:
                    p_min = pricemap[matches[0]]
                    new_lines.append(f"- PRECIO MÍNIMO SUGERIDO: ${int(p_min)}\n")
                else:
                    new_lines.append(f"- PRECIO MÍNIMO SUGERIDO: $0\n")
                    
    # Añadir Cortisol explícitamente si no existía antes
    if not any("CORTISOL" in l.upper() for l in lines):
        new_lines.append("\n## CORTISOL\n")
        new_lines.append("- PRECIO MÁXIMO SUGERIDO: $500\n")
        new_lines.append("- PRECIO MÍNIMO SUGERIDO: $300\n")
        new_lines.append("- Muestra requerida: Suero Tubo rojo o amarillo\n")
                    
    with open("conocimiento.md", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    print("Base de conocimiento actualizada con Precios Mínimos.")

if __name__ == '__main__':
    update_conocimiento()
