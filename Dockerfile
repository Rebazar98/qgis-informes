# Imagen base Ubuntu + QGIS (headless)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# QGIS y dependencias
RUN apt-get update && apt-get install -y \
    gnupg software-properties-common curl ca-certificates \
    && add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y \
    && apt-get update && apt-get install -y \
       qgis qgis-server python3-qgis gdal-bin python3-pip xvfb \
       fonts-dejavu-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Entorno gráfico offscreen y runtime
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

WORKDIR /app

# Copiamos sólo lo que necesitamos
COPY proyecto.qgz /app/proyecto.qgz
COPY capas_parcela.gpkg /app/capas_parcela.gpkg
COPY app.py /app/app.py

# 🔥 Asegurarnos de que los scripts antiguos NO están en la imagen
RUN rm -f /app/render.py /app/render_basico.py || true

# Dependencias Python para la API
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

# Puerto de escucha (Railway)
ENV PORT=8080
EXPOSE 8080

# Arrancar el servidor FastAPI con Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
