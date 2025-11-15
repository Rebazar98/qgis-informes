# Imagen oficial con QGIS, PyQGIS, Qt y todas las dependencias listas
FROM kartoza/qgis:3.34

# Configuración de entorno headless
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

# Variables requeridas por QGIS
ENV QGIS_PREFIX_PATH=/usr

# Directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY proyecto.qgz /app/proyecto.qgz
COPY app.py /app/app.py
COPY render.py /app/render.py
COPY render_basico.py /app/render_basico.py

# Instalar dependencias Python necesarias para FastAPI
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

# Puerto que Railway expone
ENV PORT=8080
EXPOSE 8080

# Comando para iniciar la API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
