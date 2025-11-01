import os
import tempfile
import subprocess
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT", "INFORME")


@app.get("/")
def root():
    return {"ok": True, "msg": "QGIS-informes API viva", "project": QGIS_PROJECT, "layout": QGIS_LAYOUT}

@app.get("/healthz")
def healthz():
    # simple chequeo de vida del proceso web
    return JSONResponse({"status": "ok"})


@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    # Fichero temporal PDF
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Variables de proyecto para el layout
    var_args: list[str] = []
    def push_var(k, v):
        var_args.extend(["--project-variables", f"{k}={v}"])

    push_var("refcat", refcat)
    if wkt_extent_parcela: push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle: push_var("wkt_extent_detalle", wkt_extent_detalle)

    # Exportar layout a PDF (ejecución headless con xvfb-run)
    cmd = [
        "xvfb-run","-a",
        "qgis_process","run","qgis:exportprintlayoutaspdf",
        "--",
        f"PROJECT_PATH={QGIS_PROJECT}",
        f"LAYOUT={QGIS_LAYOUT}",
        "DPI=300",
        "FORCE_VECTOR_OUTPUT=false",
        "GEOREFERENCE=true",
        f"OUTPUT={outpath}",
    ] + var_args

    run = subprocess.run(cmd, capture_output=True, text=True)

    if run.returncode != 0 or not os.path.exists(outpath):
        # Devolvemos stdout/stderr para depurar rápido desde logs de Railway
        raise HTTPException(
            status_code=500,
            detail={
                "error": "qgis_process failed",
                "stdout": run.stdout[-4000:],   # último bloque por si es largo
                "stderr": run.stderr[-4000:]
            }
        )

    filename = f"informe_{refcat}.pdf"
    return FileResponse(outpath, media_type="application/pdf", filename=filename)


if __name__ == "__main__":
    # ¡Clave!: usar PORT que pone Railway
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")
