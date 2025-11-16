import os
import tempfile
import subprocess
import shlex
import json
from typing import List, Tuple, Optional

from fastapi import FastAPI, Query
from fastapi.responses import (
    FileResponse,
    PlainTextResponse,
    JSONResponse,
)

app = FastAPI(title="QGIS Planos por refcat")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:atlaslayouttopdf")


def run_proc(
    cmd: List[str],
    extra_env: Optional[dict] = None,
    stdin_text: Optional[str] = None,
) -> Tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)

    if extra_env:
        env.update(extra_env)

    p = subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        env=env,
    )
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


@app.get("/render")
def render(refcat: str = Query(..., min_length=3)):
    """
    Genera el PDF del atlas filtrando por el campo "refcat" de la capa de cobertura.
    Usamos FILTER_EXPRESSION del algoritmo para limitar el atlas a esa parcela.
    """

    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Expresión de filtro que QGIS aplicará al atlas
    filter_expr = f"\"refcat\" = '{refcat}'"

    payload = {
        "inputs": {
            "LAYOUT": QGIS_LAYOUT,
            "OUTPUT": outpath,
            "FILTER_EXPRESSION": filter_expr,
            # Dejamos que use la capa de cobertura definida en el layout
        },
        "project_path": QGIS_PROJECT,
    }
    payload_json = json.dumps(payload)

    cmd: List[str] = [
        "xvfb-run",
        "-a",
        "qgis_process",
        "run",
        QGIS_ALGO,   # native:atlaslayouttopdf
        "-",         # parámetros vía JSON en stdin
    ]

    code, out, err = run_proc(cmd, stdin_text=payload_json)

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
                "payload": payload,
            },
        )

    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
