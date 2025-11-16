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

ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

WORKDIR /app

# Descargar la ortofoto desde el Release de GitHub
RUN curl -L "https://github.com/Rebazar98/qgis-informes/releases/download/v0.1.0/ortofoto_muros.tif" \
    -o /app/ortofoto_muros.tif

# Proyecto y datos vectoriales
COPY proyecto.qgz  /app/proyecto.qgz
COPY parcela.gpkg /app/parcela.gpkg
COPY app.py       /app/app.py

RUN pip3 install fastapi uvicorn[standard] pydantic

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8080"]
