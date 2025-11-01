FROM qgis/qgis:release-3.34

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip fonts-dejavu fonts-liberation tini && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py /app/app.py
COPY proyecto.qgz /app/proyecto.qgz

RUN pip3 install fastapi uvicorn[standard]

RUN mkdir -p /app/out
ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["uvicorn","app:api","--host","0.0.0.0","--port","8000"]
