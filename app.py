import os
import tempfile
import subprocess
import shlex
import json

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

# ⚙️ Config por variables de entorno (Railway)
QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:printlayouttopdf")  # de momento seguimos con este

def run_proc(cmd: list[str], stdin: str | None = None) -> tuple[int, str, str]:
    """
    Ejecuta un comando con el entorno adecuado para QGIS en modo headless.
    Si `stdin` no es None, se pasa como entrada estándar (para el modo JSON de qgis_process).
    """
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)

    p = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )
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
    """
    Renderiza el layout a PDF usando qgis_process en modo JSON.

    De momento:
    - Usa el layout `QGIS_LAYOUT`
    - Carga el proyecto `QGIS_PROJECT`
    - NO pasa aún variables de proyecto (refcat lo usaremos más adelante
      para filtros/atlas o para PostGIS).
    """

    # 1) Comprobar proyecto
    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Proyecto no encontrado",
                "path": QGIS_PROJECT,
            },
        )

    # 2) Salida temporal
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # 3) Construir payload JSON para qgis_process
    #    Véase documentación: se pasa un objeto con "inputs" y "project_path"
    inputs: dict[str, object] = {
        "LAYOUT": QGIS_LAYOUT,
        "DPI": 300,
        "FORCE_VECTOR_OUTPUT": False,
        "GEOREFERENCE": True,
        "OUTPUT": outpath,
    }

    # (Extents en WKT – guardados por ahora, los usaremos más adelante)
    if wkt_extent_parcela:
        inputs["EXTENT_PARCELA"] = wkt_extent_parcela
    if wkt_extent_detalle:
        inputs["EXTENT_DETALLE"] = wkt_extent_detalle

    payload = {
        "inputs": inputs,
        "project_path": QGIS_PROJECT,
        # ⚠️ Más adelante podremos usar esto si confirmamos soporte:
        # "project_variables": {"refcat": refcat},
    }

    payload_str = json.dumps(payload)

    # 4) Comando qgis_process: modo JSON por stdin (el "-" final)
    cmd = [
        "xvfb-run",
        "-a",
        "qgis_process",
        "run",
        QGIS_ALGO,
        "-",
    ]

    code, out, err = run_proc(cmd, stdin=payload_str)

    # 5) Control de errores
    if code != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis_process failed",
                "cmd": " ".join(shlex.quote(c) for c in cmd),
                "stdin": payload,
                "stdout": out,
                "stderr": err,
            },
        )

    # 6) Devolver PDF
    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
