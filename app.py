import os, tempfile, subprocess, shlex
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "INFORME")
QGIS_ALGO    = os.getenv("QGIS_ALGO",    "native:printlayout")  # QGIS 3.34 suele usar este

def run_proc(cmd: list[str]) -> tuple[int,str,str]:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
    # Asegura el directorio en runtime (algunos hosts lo borran en cada arranque)
    os.makedirs(env["XDG_RUNTIME_DIR"], exist_ok=True)
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr

@app.get("/qgis")
def qgis_info():
    code, out, err = run_proc(["qgis_process","--version"])
    return {"qgis_process": "/usr/bin/qgis_process", "code": code, "stdout": out, "stderr": err}

@app.get("/algos", response_class=PlainTextResponse)
def list_algos(filter: str | None = None):
    # Lista de algoritmos y filtro opcional (p.e. ?filter=layout)
    code, out, err = run_proc(["qgis_process","list"])
    if code != 0:
        return PlainTextResponse(f"ERROR list:\nSTDOUT:\n{out}\n\nSTDERR:\n{err}", status_code=500)
    if filter:
        lines = [ln for ln in out.splitlines() if filter.lower() in ln.lower()]
        return PlainTextResponse("\n".join(lines) or "(sin coincidencias)")
    return PlainTextResponse(out)

@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    # PDF temporal
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Variables de proyecto para el layout (QGIS → Variables del diseño)
    var_args: list[str] = []
    def push_var(k, v):
        var_args.extend(["--project-variables", f"{k}={v}"])
    push_var("refcat", refcat)
    if wkt_extent_parcela: push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle: push_var("wkt_extent_detalle", wkt_extent_detalle)

    # Elegir algoritmo desde env (por si quieres probar otro sin redeployar código)
    algo = QGIS_ALGO  # p.ej. native:printlayout

    # Parámetros según algoritmo:
    # - native:printlayout → LAYOUT (nombre), DPI, FORCE_VECTOR_OUTPUT, GEOREFERENCE, OUTPUT
    cmd = [
        "xvfb-run","-a",
        "qgis_process","run", algo,
        "--",
        f"PROJECT_PATH={QGIS_PROJECT}",
        f"LAYOUT={QGIS_LAYOUT}",
        "DPI=300",
        "FORCE_VECTOR_OUTPUT=false",
        "GEOREFERENCE=true",
        f"OUTPUT={outpath}",
    ] + var_args

    code, out, err = run_proc(cmd)
    if code != 0 or not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        # Devuelve diagnóstico completo
        return JSONResponse(
            status_code=500,
            content={
                "error": "qgis_process failed",
                "cmd": " ".join(shlex.quote(c) for c in cmd),
                "stdout": out,
                "stderr": err,
            },
        )

    filename = f"informe_{refcat}.pdf"
    return FileResponse(outpath, media_type="application/pdf", filename=filename)
