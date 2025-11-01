import os, subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

api = FastAPI()
QGZ = "/app/proyecto.qgz"
LAYOUT = "Informe"   # nombre EXACTO de tu layout en QGIS

def run_qgis(refcat, wkt_parcela, wkt_detalle):
    out_pdf = f"/app/out/informe_{refcat}.pdf"
    subs = f"refcat={refcat},wkt_extent_parcela={wkt_parcela},wkt_extent_detalle={wkt_detalle}"
    cmd = [
        "qgis_process","run","qgis:exportlayoutaspdf",
        "--","PROJECT_PATH="+QGZ,
        "LAYOUT="+LAYOUT,
        "DPI=300","GEOREFERENCE=false","EXPORT_METADATA=false",
        "OUTPUT="+out_pdf,
        "--","SUBSTITUTE_VARIABLES="+subs
    ]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"qgis_process error: {e}")

    if not os.path.exists(out_pdf):
        raise HTTPException(status_code=500, detail="PDF no generado")

    return out_pdf

@api.post("/render")
def render(payload: dict):
    try:
        refcat = payload["refcat"]
        wkt_parcela = payload["wkt_extent_parcela"]
        wkt_detalle = payload["wkt_extent_detalle"]
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Falta campo: {e}")

    pdf_path = run_qgis(refcat, wkt_parcela, wkt_detalle)
    return FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))
