@app.get("/render")
def render(
    refcat: str = Query(..., min_length=3),
):
    """
    Genera el PDF del plano urbanístico para la parcela cuyo refcat se pasa.
    El Atlas del layout debe tener el filtro: "refcat" = env('REFCAT')
    """

    if not os.path.exists(QGIS_PROJECT):
        return JSONResponse(
            status_code=500,
            content={"error": "Proyecto no encontrado", "path": QGIS_PROJECT},
        )

    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # NUEVO COMANDO: sin --project-path
    cmd = [
        "xvfb-run",
        "-a",
        "qgis_process",
        "run",
        QGIS_ALGO,            # native:printlayouttopdf
        "--",                 # parámetros del algoritmo
        f"LAYOUT={QGIS_LAYOUT}",
        "DPI=300",
        "FORCE_VECTOR_OUTPUT=false",
        "GEOREFERENCE=true",
        f"OUTPUT={outpath}",
    ]

    # Variables de entorno:
    # - REFCAT para el filtro del Atlas ("refcat" = env('REFCAT'))
    # - QGIS_PROJECT_FILE para que QGIS sepa qué proyecto cargar
    extra_env = {
        "REFCAT": refcat,
        "QGIS_PROJECT_FILE": QGIS_PROJECT,
    }

    code, out, err = run_proc(cmd, extra_env=extra_env)

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

    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename=f"informe_{refcat}.pdf",
    )