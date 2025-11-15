import sys
import os
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsLayoutExporter,
    QgsPrintLayout,
)

# Leer argumentos de entrada
refcat = None
output = None
for arg in sys.argv:
    if arg.startswith("--refcat="):
        refcat = arg.split("=", 1)[1]
    elif arg.startswith("--output="):
        output = arg.split("=", 1)[1]

if not refcat or not output:
    print("ERROR: Faltan parámetros --refcat= o --output=")
    sys.exit(1)

project_path = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
layout_name  = os.getenv("QGIS_LAYOUT", "Plano_urbanistico_parcela")

# Iniciar la aplicación QGIS sin GUI
qgs = QgsApplication([], False)
qgs.initQgis()

# Cargar el proyecto
project = QgsProject.instance()
project.read(project_path)

# Establecer variable de proyecto
project.setCustomVariables({'refcat': refcat})

# Buscar el layout
manager = project.layoutManager()
layout = next((l for l in manager.printLayouts() if l.name() == layout_name), None)

if not layout:
    print(f"ERROR: Layout '{layout_name}' no encontrado")
    qgs.exitQgis()
    sys.exit(1)

# Exportar el atlas
exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.rasterizeWholeImage = False
result = exporter.exportToPdf(output, settings)

if result != QgsLayoutExporter.Success:
    print(f"ERROR: Falló la exportación con código {result}")
    qgs.exitQgis()
    sys.exit(1)

print(f"PDF generado en {output}")
qgs.exitQgis()
