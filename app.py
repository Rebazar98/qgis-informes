QGIS_RENDER_SCRIPT = "render_basico.py"

@app.get("/render_test")
def render_test():
    fd, outpath = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    cmd = [
        "xvfb-run", "-a",
        "qgis",
        "--nologo",
        "--code", QGIS_RENDER_SCRIPT,
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
                "error": "render_basico falló",
                "cmd": " ".join(cmd),
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            },
        )

    return FileResponse(
        outpath,
        media_type="application/pdf",
        filename="test_export.pdf",
    )
