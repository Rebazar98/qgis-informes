import os, tempfile, subprocess
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT", "INFORME")  # pon el nombre exacto del layout

@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    # Fichero temporal PDF
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Variables de proyecto (para que tu layout las recoja)
    var_args: list[str] = []
    def push_var(k, v):
        var_args.extend(["--project-variables", f"{k}={v}"])

    push_var("refcat", refcat)
    if wkt_extent_parcela: push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle: push_var("wkt_extent_detalle", wkt_extent_detalle)

    # qgis_process exporta el layout a PDF (xvfb-run para headless)
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
        raise HTTPException(500, f"QGIS falló:\nSTDOUT:\n{run.stdout}\n\nSTDERR:\n{run.stderr}")

    # Devuelve el PDF
    filename = f"informe_{refcat}.pdf"
    return FileResponse(outpath, media_type="application/pdf", filename=filename)
