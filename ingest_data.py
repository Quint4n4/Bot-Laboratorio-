import sys
from rag import get_embedding
from database import supabase

def parse_estudios(filepath: str) -> list[dict]:
    """
    Lee conocimiento.md y devuelve una lista de dicts, uno por estudio.
    Cada dict tiene: 'nombre', 'content' (listo para embeddings).
    También incluye las secciones de recomendaciones como documentos adicionales.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    estudios = []
    current_title = None
    current_lines = []

    for line in text.split("\n"):
        if line.startswith("## "):
            # Guardar el estudio anterior si existe
            if current_title and current_lines:
                content = f"{current_title}\n" + "\n".join(current_lines)
                estudios.append({"nombre": current_title, "content": content.strip()})
            # Iniciar nuevo estudio
            current_title = line[3:].strip()
            current_lines = []
        elif line.startswith("# "):
            # Encabezado principal (lo ignoramos como estudio individual)
            if current_title and current_lines:
                content = f"{current_title}\n" + "\n".join(current_lines)
                estudios.append({"nombre": current_title, "content": content.strip()})
            current_title = None
            current_lines = []
        else:
            if current_title:
                current_lines.append(line)

    # Guardar el último
    if current_title and current_lines:
        content = f"{current_title}\n" + "\n".join(current_lines)
        estudios.append({"nombre": current_title, "content": content.strip()})

    return estudios


def ingest_file(filepath: str = "conocimiento.md"):
    """Lee el catálogo e indexa cada estudio como documento individual en Supabase."""
    print(f"📖 Parseando '{filepath}'...")
    estudios = parse_estudios(filepath)
    print(f"🧩 Se encontraron {len(estudios)} entradas (estudios + secciones).")

    print("🧹 Limpiando documentos anteriores en Supabase...")
    try:
        supabase.table("documents").delete().neq("id", -1).execute()
    except Exception as e:
        print("  ⚠️  Error al limpiar (continuando):", e)

    ok = 0
    fail = 0
    for i, estudio in enumerate(estudios):
        nombre = estudio["nombre"]
        content = estudio["content"]

        # Saltar entradas vacías o muy cortas
        if len(content.strip()) < 10:
            continue

        try:
            vector = get_embedding(content)
            data = {
                "content": content,
                "metadata": {
                    "source": filepath,
                    "nombre": nombre,
                    "index": i
                },
                "embedding": vector
            }
            supabase.table("documents").insert(data).execute()
            print(f"  ✅ [{i+1}/{len(estudios)}] {nombre}")
            ok += 1
        except Exception as e:
            print(f"  ❌ [{i+1}/{len(estudios)}] Error en '{nombre}': {e}")
            fail += 1

    print(f"\n🎉 Ingestión completada: {ok} exitosos, {fail} fallidos.")


if __name__ == "__main__":
    ingest_file("conocimiento.md")
