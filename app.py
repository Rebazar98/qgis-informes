import os, tempfile, subprocess, shutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT", "INFORME")

@app.get("/")
def root():
    return {"ok": True, "project": QGIS_PROJECT, "layout": QGIS_LAYOUT}

@app.get("/qgis")
def qgis_info():
    exe = shutil.which("qgis_process")
    run = subprocess.run(["qgis_process","--version"], capture_output=True, text=True)
    return {"qgis_process": exe, "stdout": run.stdout, "stderr": run.stderr, "code": run.returncode}

@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    var_args: list[str] = []
    def push_var(k, v):
        var_args.extend(["--project-variables", f"{k}={v}"])

    push_var("refcat", refcat)
    if wkt_extent_parcela: push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle: push_var("wkt_extent_detalle", wkt_extent_detalle)

    # try con provider moderno y fallback al antiguo
    algos = [
        "native:exportprintlayoutaspdf",
        "qgis:exportprintlayoutaspdf"
    ]

    last = None
    for ALG in algos:
        cmd = [
            "xvfb-run","-a","qgis_process","run", ALG,
            "--",
            f"PROJECT_PATH={QGIS_PROJECT}",
            f"LAYOUT={QGIS_LAYOUT}",
            "DPI=300",
            "FORCE_VECTOR_OUTPUT=false",
            "GEOREFERENCE=true",
            f"OUTPUT={outpath}",
        ] + var_args

        run = subprocess.run(cmd, capture_output=True, text=True)
        last = {"cmd":" ".join(cmd), "stdout": run.stdout, "stderr": run.stderr, "code": run.returncode}

        if run.returncode == 0 and os.path.exists(outpath):
            return FileResponse(outpath, media_type="application/pdf", filename=f"informe_{refcat}.pdf")

    raise HTTPException(500, detail={"error":"qgis_process failed", **last})
