import os
import tempfile
import subprocess
import shlex
import json
from typing import List, Tuple, Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Planos por refcat")

# Config desde variables de entorno (Railway) o por defecto
QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:atlaslayouttopdf")


def run_proc(
    cmd: List[str],
    extra_env: Optional[dict] = None,
    stdin_text: Optional[str] = None,
    timeout: int = 120,
) -> Tuple[int, str, str]:
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

    try:
        p = subprocess.run(
            cmd,
            input=stdin_text,
            text=True,
            capture_output=True,
            env=env,
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        # Devolvemos un código tipo 124 para identificar timeout
        return 124, e.stdout or "", (e.stderr or "") + "\n[TIMEOUT EXPIRED]"


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
    debug: int = Query(0, description="Si !=0, devuelve JSON de debug en vez del PDF"),
):
    """
    Genera el PDF del atlas para la parcela cuyo refcat se pasa.

    En el proyecto QGIS, el atlas del layout debe tener:
        - Capa cobertura = 'parcelas'
        - Filtrar con = "refcat" = env('REFCAT')

    Aquí solo seteamos la variable de entorno REFCAT y llamamos
    a native:atlaslayouttopdf.
    """

    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    # Fichero temporal de salida
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Payload JSON para qgis_process (sin FILTER_EXPRESSION)
    payload = {
        "inputs": {
            "LAYOUT": QGIS_LAYOUT,
            "OUTPUT": outpath,
        },
        "project_path": QGIS_PROJECT,
    }
    payload_json = json.dumps(payload)

    cmd: List[str] = [
        "xvfb-run",
        "-a",
        "qgis_process",
        "run",
        QGIS_ALGO,  # native:atlaslayouttopdf
        "-",        # lee JSON por stdin
    ]

    extra_env = {
        "REFCAT": refcat,
    }

    code, out, err = run_proc(cmd, extra_env=extra_env, stdin_text=payload_json)

    # Modo debug: devolvemos toda la info
    if debug:
        info = {
            "refcat": refcat,
            "cmd": " ".join(shlex.quote(c) for c in cmd),
            "stdout": out,
            "stderr": err,
            "exit_code": code,
            "output_exists": os.path.exists(outpath),
            "output_size": os.path.getsize(outpath) if os.path.exists(outpath) else 0,
            "payload": payload,
        }
        return JSONResponse(info)

    # Errores o PDF vacío
    if code != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis_process failed",
                "cmd": " ".join(shlex.quote(c) for c in cmd),
                "stdout": out,
                "stderr": err,
                "exit_code": code,
                "output_exists": os.path.exists(outpath),
                "output_size": os.path.getsize(outpath) if os.path.exists(outpath) else 0,
                "payload": payload,
            },
        )

    # OK -> devolvemos el PDF
    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
