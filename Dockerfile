# Imagen base Ubuntu + QGIS (headless)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV QT_QPA_PLATFORM=offscreen
# Puerto por defecto (Railway sobreescribe PORT)
ENV PORT=8000

# QGIS y dependencias del sistema
RUN apt-get update && apt-get install -y \
    gnupg software-properties-common curl ca-certificates locales && \
    locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8 && \
    add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y && \
    apt-get update && apt-get install -y \
    qgis qgis-server python3-qgis gdal-bin python3-pip xvfb \
    fonts-dejavu-core && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# App
WORKDIR /app
COPY proyecto.qgz /app/proyecto.qgz
COPY app.py       /app/app.py

# Python (FastAPI + Uvicorn)
RUN pip3 install --no-cache-dir "fastapi" "uvicorn[standard]" "pydantic"

# Healthcheck (usa la variable PORT, por defecto 8000)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Exponer el puerto (informativo)
EXPOSE 8000

# Ejecutar Uvicorn respetando PORT (Railway la inyecta)
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
