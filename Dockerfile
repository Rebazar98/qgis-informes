# Imagen base Ubuntu + QGIS (headless)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# QGIS y dependencias
RUN apt-get update && apt-get install -y \
    gnupg software-properties-common curl ca-certificates && \
    add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y && \
    apt-get update && apt-get install -y \
    qgis qgis-server python3-qgis gdal-bin python3-pip xvfb \
    fonts-dejavu-core && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Variables que ayudan a que QGIS funcione en contenedor
ENV QT_QPA_PLATFORM=offscreen
ENV QGIS_PREFIX_PATH=/usr
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8

# App
WORKDIR /app
COPY proyecto.qgz /app/proyecto.qgz
COPY app.py /app/app.py

# Python web
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

# Railway inyecta PORT; no fijamos un valor fijo aquí
EXPOSE 8000

# Ejecutamos el módulo Python para que respete el PORT del entorno
CMD ["python3", "/app/app.py"]
