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

# App
WORKDIR /app
COPY proyecto.qgz /app/proyecto.qgz
COPY app.py /app/app.py

# Python web
RUN pip3 install fastapi uvicorn[standard] pydantic

EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]

