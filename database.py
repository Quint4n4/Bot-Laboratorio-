from supabase import create_client, Client
from config import settings

# Inicializamos el cliente de Supabase de manera global.
# Puedes importar `supabase` desde este archivo en otras partes de tu proyecto.
supabase: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_KEY
)

def ping_db() -> bool:
    """Verifica la conectividad básica con Supabase."""
    try:
        # Hacemos una consulta rápida a alguna tabla existente o simplemente pedimos datos
        # Si tienes una tabla específica para testear, puedes ponerla aquí
        # Por ejemplo: response = supabase.table("users").select("*").limit(1).execute()
        return True
    except Exception as e:
        print(f"❌ Error al conectar con Supabase: {e}")
        return False
