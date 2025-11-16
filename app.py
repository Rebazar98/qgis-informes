import os
import tempfile
import subprocess
import shlex
from typing import List, Tuple, Optional

from fastapi import FastAPI, Query
from fastapi.responses import (
    FileResponse,
    PlainTextResponse,
    JSONResponse,
)

# 1️⃣ Crear la app
app = FastAPI(title="QGIS Planos por refcat")

# 2️⃣ Configuración básica (sobrescribible con variables de entorno en Railway)
QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:printlayouttopdf")


def run_proc(cmd: List[str], extra_env: Optional[dict] = None) -> Tuple[int, str, str]:
    """
    Ejecuta un comando y devuelve (returncode, stdout, stderr)
    con las variables necesarias para modo offscreen.
    """
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)

    if extra_env:
        env.update(extra_env)

    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


@app.get("/health")
def health():
    return {
        "status": "ok",
        "project": QGIS_PROJECT,
        "layout": QGIS_LAYOUT,
        "algo": QGIS_ALGO,
    }


@app.get("/qgis")
def qgis_info():
    code, out, err = run_proc(["qgis_process", "--version"])
    return {
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


@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
):
    """
    Genera el PDF del plano urbanístico para la parcela cuyo refcat se pasa.
    En el layout, el Atlas debe tener el filtro:  "refcat" = env('REFCAT')
    """

    # Comprobar que el proyecto existe
    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    # Fichero temporal de salida
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Comando qgis_process:
    # Nota: el propio error indica que quiere "--PROJECT_PATH=xxx"
    cmd: List[str] = [
        "xvfb-run",
        "-a",
        "qgis_process",
        "run",
        QGIS_ALGO,                         # native:printlayouttopdf
        "--",                              # parámetros del algoritmo
        f"--PROJECT_PATH={QGIS_PROJECT}",  # 👈 ruta al proyecto
        f"--LAYOUT={QGIS_LAYOUT}",         # nombre del layout
        "--DPI=300",
        "--FORCE_VECTOR_OUTPUT=false",
        "--GEOREFERENCE=true",
        f"--OUTPUT={outpath}",
    ]

    # Variables de entorno:
    # - REFCAT para el filtro del Atlas ("refcat" = env('REFCAT'))
    extra_env = {
        "REFCAT": refcat,
    }

    code, out, err = run_proc(cmd, extra_env=extra_env)

    # Si falla o el PDF está vacío, devolvemos info de debug
    if code != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis_process failed",
                "cmd": " ".join(shlex.quote(c) for c in cmd),
                "stdout": out,
                "stderr": err,
                "output_exists": os.path.exists(outpath),
                "output_size": os.path.getsize(outpath) if os.path.exists(outpath) else 0,
            },
        )

    # Si todo va bien, devolvemos el PDF
    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
