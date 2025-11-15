import sys
import os
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsLayoutExporter
)

output = None
for arg in sys.argv:
    if arg.startswith("--output="):
        output = arg.split("=", 1)[1]

if not output:
    print("ERROR: falta --output=")
    sys.exit(1)

project_path = os.getenv("QGIS_PROJECT", "/app/proyecto.qgz")
layout_name  = os.getenv("QGIS_LAYOUT", "Plano_urbanistico_parcela")

# Inicializar QGIS
QgsApplication.setPrefixPath("/usr", True)
qgs = QgsApplication([], False)
qgs.initQgis()

# Cargar proyecto
project = QgsProject.instance()
if not project.read(project_path):
    print("ERROR: No se pudo leer el proyecto")
    sys.exit(1)

# Obtener layout
manager = project.layoutManager()
layout = next((l for l in manager.printLayouts() if l.name() == layout_name), None)

if not layout:
    print(f"ERROR: Layout '{layout_name}' no encontrado")
    sys.exit(1)

# Exportar sin atlas
exporter = QgsLayoutExporter(layout)
result = exporter.exportToPdf(output, QgsLayoutExporter.PdfExportSettings())

if result != QgsLayoutExporter.Success:
    print(f"ERROR: exportación falló con código {result}")
    sys.exit(1)

print(f"PDF exportado correctamente: {output}")
