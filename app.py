import os, tempfile, subprocess, shutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT", "INFORME")  # nombre exacto del layout

@app.get("/")
def root():
    return {"ok": True, "msg": "qgis-informes vivo", "project": QGIS_PROJECT, "layout": QGIS_LAYOUT}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/qgis")
def qgis_info():
    # Comprobar qgis_process disponible y versión
    exe = shutil.which("qgis_process")
    if not exe:
        return JSONResponse({"qgis_process": None, "error": "qgis_process no encontrado en PATH"}, status_code=500)
    run = subprocess.run(["qgis_process","--version"], capture_output=True, text=True)
    return {"qgis_process": exe, "stdout": run.stdout, "stderr": run.stderr, "code": run.returncode}

@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    # Fichero temporal PDF
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Variables de proyecto (para que el layout las recoja)
    var_args: list[str] = []
    def push_var(k, v):
        var_args.extend(["--project-variables", f"{k}={v}"])

    push_var("refcat", refcat)
    if wkt_extent_parcela: push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle: push_var("wkt_extent_detalle", wkt_extent_detalle)

    # Ejecutar QGIS en headless
    cmd = [
        "xvfb-run","-a","qgis_process","run","qgis:exportprintlayoutaspdf",
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
        # Mostrar error útil (algoritmo no encontrado, etc.)
        raise HTTPException(
            500,
            detail={
                "error": "qgis_process failed",
                "stdout": run.stdout,
                "stderr": run.stderr,
                "cmd": " ".join(cmd)
            }
        )

    return FileResponse(outpath, media_type="application/pdf", filename=f"informe_{refcat}.pdf")
