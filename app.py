import os, tempfile, subprocess, shlex
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

app = FastAPI(title="QGIS Informe Urbanístico")

QGIS_PROJECT = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
QGIS_LAYOUT  = os.getenv("QGIS_LAYOUT",  "INFORME")

# Candidatas de algoritmo según versión de QGIS
ALG_CANDIDATES = [
    "native:exportlayouttopdf",
    "native:layouttopdf",
    "qgis:layouttopdf",
    "qgis:exportprintlayoutaspdf",
]

def run_cmd(cmd:list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)

@app.get("/", response_class=PlainTextResponse)
def root():
    return f"OK - project={QGIS_PROJECT} layout={QGIS_LAYOUT}"

@app.get("/healthz")
def healthz():
    return {"status":"ok"}

@app.get("/algos", response_class=PlainTextResponse)
def algos():
    """
    Devuelve la lista completa de algoritmos para depurar en runtime.
    Útil si ninguna candidate funciona.
    """
    p = run_cmd(["qgis_process","help"])
    if p.returncode != 0:
        return f"qgis_process help failed\n\nSTDOUT:\n{p.stdout}\n\nSTDERR:\n{p.stderr}"
    return p.stdout

def try_export_with(algo_id: str, outpath: str, var_args: list[str]) -> subprocess.CompletedProcess:
    # Parámetros comunes de layout->PDF (nativos y qgis suelen aceptar estos nombres)
    params = [
        f"PROJECT_PATH={QGIS_PROJECT}",
        f"LAYOUT={QGIS_LAYOUT}",
        "DPI=300",
        "FORCE_VECTOR_OUTPUT=false",
        "GEOREFERENCE=true",
        f"OUTPUT={outpath}",
    ]
    cmd = ["xvfb-run","-a","qgis_process","run",algo_id,"--"] + params + var_args
    return run_cmd(cmd)

@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
    wkt_extent_parcela: str | None = None,
    wkt_extent_detalle: str | None = None
):
    # Fichero temporal para el PDF
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Variables del proyecto (para el layout)
    var_args: list[str] = []
    def push_var(k, v):
        var_args.extend(["--project-variables", f"{k}={v}"])

    push_var("refcat", refcat)
    if wkt_extent_parcela: push_var("wkt_extent_parcela", wkt_extent_parcela)
    if wkt_extent_detalle: push_var("wkt_extent_detalle", wkt_extent_detalle)

    # Probar algoritmos candidatos hasta que uno exista/funcione
    last_stdout, last_stderr = "", ""
    for algo in ALG_CANDIDATES:
        p = try_export_with(algo, outpath, var_args)
        if p.returncode == 0 and os.path.exists(outpath) and os.path.getsize(outpath) > 0:
            filename = f"informe_{refcat}.pdf"
            return FileResponse(outpath, media_type="application/pdf", filename=filename)
        # Guardamos logs por si hay que reportar
        last_stdout, last_stderr = p.stdout, p.stderr

        # Si el mensaje fue "Algorithm ... not found", seguimos con el siguiente
        if "not found" in (p.stdout + p.stderr).lower():
            continue
        # Si falló por otra razón, rompemos para reportar ese error
        break

    # Si llegó aquí, no se encontró/funcionó ninguna ID
    # Adjuntamos un extracto de /algos para ayudarte a localizar la correcta
    help_info = run_cmd(["qgis_process","help"]).stdout
    raise HTTPException(
        500,
        detail={
            "error":"qgis_process failed",
            "tried_algorithms": ALG_CANDIDATES,
            "stdout": last_stdout[-4000:],   # últimos 4KB para no saturar
            "stderr": last_stderr[-4000:],
            "hint": "Abre /algos para ver todas las IDs disponibles y ajusta ALG_CANDIDATES si hace falta.",
            "algos_sample": help_info[:4000]  # muestra inicial del listado
        }
    )
