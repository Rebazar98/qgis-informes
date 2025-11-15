# Imagen pública de QGIS funcional y headless
FROM qgis/qgis:release-3_16

# Entorno gráfico offscreen y runtime
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

# Variables necesarias para PyQGIS
ENV QGIS_PREFIX_PATH=/usr

WORKDIR /app

# Copiar archivos del proyecto
COPY proyecto.qgz /app/proyecto.qgz
COPY app.py /app/app.py
COPY render.py /app/render.py
COPY render_basico.py /app/render_basico.py

# Instalar dependencias de FastAPI
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

# Puerto que Railway expone
ENV PORT=8080
EXPOSE 8080

# Lanzar el servidor FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
