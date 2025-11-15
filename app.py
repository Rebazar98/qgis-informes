import os
import tempfile
import subprocess
import shlex
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

app = FastAPI(title="QGIS Informe Urbanístico")

@app.get("/health")
def health():
    return {"status": "ok", "mode": "script render.py"}

def run_proc(cmd: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)

    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr

@app.get("/render")
def render(refcat: str = Query(..., min_length=3)):
    """
    Ejecuta QGIS con render.py pasándole la refcat y genera un PDF.
    """
    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    cmd = [
        "xvfb-run",
        "-a",
        "qgis",
        "--nologo",
        "--code", "render.py",
        f"--refcat={refcat}",
        f"--output={output_path}",
    ]

    code, out, err = run_proc(cmd)

    if code != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis script failed",
                "refcat": refcat,
                "cmd": " ".join(shlex.quote(c) for c in cmd),
                "stdout": out,
                "stderr": err,
            },
        )

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )
