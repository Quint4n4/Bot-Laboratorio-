FROM python:3.12-slim

# Instalar ffmpeg para manejar audios de Whisper y ElevenLabs
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Comando de arranque
CMD ["python", "main.py"]
