# ==============================================================================
# Dockerfile para Study Timetrial
# Entorno reproducible para desarrollo, CI/CD y ejecución de tests headless (offscreen)
# ==============================================================================

FROM python:3.11-slim

# Evitar prompts interactivos durante instalación de paquetes Debian
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV QT_QPA_PLATFORM=offscreen

# Instalar dependencias nativas del sistema requeridas por Qt6 / PySide6 y audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libx11-xcb1 \
    libxcb-cursor0 \
    libxcb-glx0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libpulse0 \
    libasound2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo del proyecto
COPY . .

# Comando por defecto: ejecutar la suite completa de pruebas unitarias en modo headless
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
