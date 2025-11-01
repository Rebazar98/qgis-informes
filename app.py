import os
import tempfile
import subprocess
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

# Config desde variables de entorno (Railway -> Variables)
QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT", "INFORME")  # nombre exacto del layout

@app.get("/")
def root():
    """Página base para comprobar que el servicio está arriba."""
    return {
        "ok": True,
        "service": "qgis-informes",
        "message": "Servidor QGIS operativo",
        "project": QGIS_PROJECT,
        "layout": QGIS_LAYOUT,
        "docs": "/docs",
        "render_example": "/render?refcat=TEST"
    }

@app.get("/health")
def health():
    """Endpoint simple de salud para probes."""
    return {"status": "ok"}

@app.get("/info")
def info():
    """Devuelve la configuración efectiva del servicio."""
    exists = os.path.exists(QGIS_PROJECT)
    return {
        "QGIS_PROJECT": QGIS_PROJECT,
        "QGIS_LAYOUT": QGIS_LAYOUT,
        "project_exists": exists
    }

@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    """
    Exporta el layout de QGIS a PDF usando qgis_process (headless con xvfb-run).
    Rellena variables de proyecto: refcat, wkt_extent_parcela, wkt_extent_detalle.
    """
    # Fichero temporal PDF
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Variables de proyecto (para que tu layout las recoja)
    var_args: list[str] = []

    def push_var(k: str, v: str):
        # Puedes pasar varias con múltiples --project-variables K=V
        var_args.extend(["--project-variables", f"{k}={v}"])

    push_var("refcat", refcat)
    if wkt_extent_parcela:
        push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle:
        push_var("wkt_extent_detalle", wkt_extent_detalle)

    # qgis_process exporta el layout a PDF (xvfb-run para modo headless)
    cmd = [
        "xvfb-run", "-a",
        "qgis_process", "run", "qgis:exportprintlayoutaspdf",
        "--",
        f"PROJECT_PATH={QGIS_PROJECT}",
        f"LAYOUT={QGIS_LAYOUT}",
        "DPI=300",
        "FORCE_VECTOR_OUTPUT=false",
        "GEOREFERENCE=true",
        f"OUTPUT={outpath}",
    ] + var_args

    run = subprocess.run(cmd, capture_output=True, text=True)

    if run.returncode != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        # Borra el archivo vacío si falló
        try:
            if os.path.exists(outpath):
                os.remove(outpath)
        finally:
            pass
        raise HTTPException(
            status_code=500,
            detail={
                "error": "QGIS export failed",
                "stdout": run.stdout,
                "stderr": run.stderr,
                "cmd": cmd
            }
        )

    # Devuelve el PDF (Railway lo sirve inline/descarga)
    filename = f"informe_{refcat}.pdf"
    return FileResponse(outpath, media_type="application/pdf", filename=filename)


# Permite arrancar localmente con: python app.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
