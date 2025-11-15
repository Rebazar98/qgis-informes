import os
import tempfile
import subprocess
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_RENDER_SCRIPT = "render.py"  # archivo que acabamos de crear
QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "Plano_urbanistico_parcela")

@app.get("/render")
def render(refcat: str = Query(..., min_length=3)):
    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    cmd = [
        "xvfb-run", "-a",
        "qgis",
        "--nologo",
        "--code", QGIS_RENDER_SCRIPT,
        f"--refcat={refcat}",
        f"--output={outpath}"
    ]

    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if proc.returncode != 0 or not os.path.exists(outpath):
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis script failed",
                "refcat": refcat,
                "cmd": " ".join(cmd),
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            },
        )

    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
