import os
import tempfile
import subprocess
import json
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:printlayouttopdf")

def run_proc_json(algo: str, payload: dict) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)

    p = subprocess.run(
        ["xvfb-run", "-a", "qgis_process", "run", algo, "-"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return p.returncode, p.stdout, p.stderr

@app.get("/render")
def render(refcat: str = Query(..., min_length=3)):

    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    payload = {
        "project_path": QGIS_PROJECT,
        "project_variables": {
            "refcat": refcat
        },
        "inputs": {
            "LAYOUT": QGIS_LAYOUT,
            "DPI": 300,
            "FORCE_VECTOR_OUTPUT": False,
            "GEOREFERENCE": True,
            "OUTPUT": outpath,
        }
    }

    code, out, err = run_proc_json(QGIS_ALGO, payload)

    if code != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis_process failed (JSON mode)",
                "refcat": refcat,
                "project_variables": payload["project_variables"],
                "json_payload": payload,
                "stdout": out,
                "stderr": err,
            },
        )

    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
