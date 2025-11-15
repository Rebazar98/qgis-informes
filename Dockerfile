# Imagen válida y funcional con QGIS 3.34
FROM kartoza/qgis:release-3_34

ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

ENV QGIS_PREFIX_PATH=/usr

WORKDIR /app

COPY proyecto.qgz /app/proyecto.qgz
COPY app.py /app/app.py
COPY render.py /app/render.py
COPY render_basico.py /app/render_basico.py

RUN pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

