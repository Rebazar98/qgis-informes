import os
import tempfile
import subprocess
import shlex
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:printlayouttopdf")  # QGIS 3.34

def run_proc(cmd: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


@app.get("/qgis")
def qgis_info():
    code, out, err = run_proc(["qgis_process", "--version"])
    return {
        "qgis_process": "/usr/bin/qgis_process",
        "code": code,
        "stdout": out,
        "stderr": err,
    }


@app.get("/algos", response_class=PlainTextResponse)
def list_algos(filter: str | None = None):
    code, out, err = run_proc(["qgis_process", "list"])
    if code != 0:
        return PlainTextResponse(
            f"ERROR list:\nSTDOUT:\n{out}\n\nSTDERR:\n{err}",
            status_code=500,
        )
    if filter:
        lines = [ln for ln in out.splitlines() if filter.lower() in ln.lower()]
        return PlainTextResponse("\n".join(lines) or "(sin coincidencias)")
    return PlainTextResponse(out)


@app.get("/algohelp", response_class=PlainTextResponse)
def algo_help(algo: str = "native:printlayouttopdf"):
    code, out, err = run_proc(["qgis_process", "help", algo])
    if code != 0:
        return PlainTextResponse(
            f"ERROR help {algo}:\nSTDOUT:\n{out}\n\nSTDERR:\n{err}",
            status_code=500,
        )
    return PlainTextResponse(out)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "project": QGIS_PROJECT,
        "layout": QGIS_LAYOUT,
        "algo": QGIS_ALGO,
    }


@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None,
):
    # De momento refcat no se usa como variable de proyecto,
    # solo para el nombre del archivo de salida.

    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Sintaxis correcta:
    # qgis_process run --project_path=/app/proyecto.qgz native:printlayouttopdf -- LAYOUT=... OUTPUT=...
    cmd = [
        "xvfb-run",
        "-a",
        "qgis_process",
        "run",
        f"--project_path={QGIS_PROJECT}",
        QGIS_ALGO,
        "--",
        f"LAYOUT={QGIS_LAYOUT}",
        "DPI=300",
        "FORCE_VECTOR_OUTPUT=false",
        "GEOREFERENCE=true",
        f"OUTPUT={outpath}",
    ]

    code, out, err = run_proc(cmd)

    if code != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis_process failed",
                "cmd": " ".join(shlex.quote(c) for c in cmd),
                "stdout": out,
                "stderr": err,
            },
        )

    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
