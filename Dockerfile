# Imagen base Ubuntu + QGIS (headless)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# QGIS y dependencias
RUN apt-get update && apt-get install -y \
    gnupg software-properties-common curl ca-certificates wget locales \
    && add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y \
    && apt-get update && apt-get install -y \
       qgis qgis-server python3-qgis gdal-bin python3-pip xvfb \
       libqt5gui5 libgl1-mesa-glx libglib2.0-0 \
       fonts-dejavu-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Locales (opcional pero previene warnings)
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Entorno gráfico offscreen y runtime
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

# Prefijo QGIS y variables necesarias para scripts
ENV QGIS_PREFIX_PATH=/usr
ENV LD_LIBRARY_PATH=/usr/lib

WORKDIR /app

# Copiar archivos del proyecto
COPY proyecto.qgz /app/proyecto.qgz
COPY app.py /app/app.py
COPY render.py /app/render.py
COPY render_basico.py /app/render_basico.py

# Instalar dependencias de Python
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

# Puerto expuesto para Railway
ENV PORT=8080
EXPOSE 8080

# Ejecutar la aplicación
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

