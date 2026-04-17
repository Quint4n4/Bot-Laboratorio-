# Imagen base oficial de Python (slim para menor tamaño)
FROM python:3.12-slim

# Variables para que Playwright use su propio Chromium (no el del sistema)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema requeridas por Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias de Python primero (aprovecha cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar dependencias del sistema requeridas por Playwright/Chromium
# (incluyendo libxkbcommon y otras libs necesarias en Linux)
RUN playwright install-deps chromium

# Instalar Chromium de Playwright
RUN playwright install chromium

# Copiar el resto del código
COPY . .

# Comando de inicio
CMD ["python", "telegram_bot.py"]
