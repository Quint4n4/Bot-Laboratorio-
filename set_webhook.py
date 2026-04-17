import requests
from config import settings

def set_evolution_webhook():
    # host.docker.internal es la orden maestra que le dice a un contenedor Docker (Evolution)
    # cómo salir y hablar con tu computadora Windows donde correrá FastAPI en el port 8000
    webhook_url = "http://host.docker.internal:8000/webhook"
    
    url = f"{settings.EVOLUTION_API_URL}/webhook/set/{settings.INSTANCE_NAME}"
    headers = {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "webhook": {
            "enabled": True,
            "url": webhook_url,
            "byEvents": False, 
            "events": [
                "MESSAGES_UPSERT"
            ]
        }
    }
    
    print(f"Conectando Evolution API local hacia: {webhook_url} ...")
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        print("✅ Webhook y puente de conexión establecido con éxito.")
    except Exception as e:
        print("❌ Error configurando webhook:")
        print(e)

if __name__ == "__main__":
    set_evolution_webhook()
