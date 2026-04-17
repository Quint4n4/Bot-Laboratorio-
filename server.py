import uvicorn
from fastapi import FastAPI, Request
import requests

from config import settings
from rag import generate_rag_response

app = FastAPI()

@app.post("/webhook")
async def evolution_webhook(request: Request):
    payload = await request.json()
    
    try:
        # Evolucion V2 envía los datos adentro del campo 'data' muchas veces
        data = payload.get("data", {})
        if not data:
            data = payload
            
        message_info = data.get("message", {})
        key_info = data.get("key", {})
        
        # Ignorar los mensajes enviados por el propio bot (vital para evitar un loop infinito matemático)
        if key_info.get("fromMe", False) == True:
            return {"status": "ignored"}
            
        remote_jid = key_info.get("remoteJid")
        
        # Obtener el texto del mensaje
        text = ""
        if "conversation" in message_info:
            text = message_info["conversation"]
        elif "extendedTextMessage" in message_info:
            text = message_info["extendedTextMessage"].get("text", "")
            
        if not text or not remote_jid:
            return {"status": "ignored"}
            
        print(f"\\n📞 [NUEVO PACIENTE]: {remote_jid} -> '{text}'")
        
        # Usamos nuestra IA matemática y doctora
        ia_reply = generate_rag_response(text)
        print(f"🤖 [NUESTRO BOT]: {ia_reply}")
        
        # Enviamos de vuelta usando un post a la propia Evolution API
        send_message(remote_jid, ia_reply)
        
        return {"status": "ok"}
    except Exception as e:
        print("Error en el Webhook:", e)
        return {"status": "error"}

def send_message(remote_jid: str, text: str):
    """Envia la cotización directo al WhatsApp de regreso."""
    url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.INSTANCE_NAME}"
    headers = {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "number": remote_jid,
        "text": text,
        "delay": 1500 # Le damos un segundo de pensar para que no parezca taaan robotico
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

if __name__ == "__main__":
    print("🏥 Recepción Médica Bot iniciando en puerto 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
