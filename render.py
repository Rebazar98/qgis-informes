import sys
import argparse
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsLayoutExporter,
    QgsReadWriteContext,
)

def render_pdf(refcat, output_path):
    # Inicializar QGIS en modo sin interfaz
    app = QgsApplication([], False)
    app.setPrefixPath("/usr", True)
    app.initQgis()

    try:
        # Cargar proyecto
        project = QgsProject.instance()
        project.read('/app/proyecto.qgz')
        if not project.fileName():
            print("❌ Error cargando el proyecto")
            sys.exit(1)

        # Establecer variable de proyecto 'refcat'
        project.setCustomVariables({'refcat': refcat})

        # Obtener el layout por nombre
        layout_manager = project.layoutManager()
        layout = layout_manager.layoutByName("Plano_urbanistico_parcela")
        if layout is None:
            print("❌ No se encontró el layout")
            sys.exit(1)

        # Exportar a PDF
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(output_path, QgsLayoutExporter.PdfExportSettings())

        if result != QgsLayoutExporter.Success:
            print("❌ Falló la exportación del PDF")
            sys.exit(1)

        print(f"✅ PDF generado: {output_path}")

    finally:
        app.exitQgis()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Renderizar PDF urbanístico con refcat")
    parser.add_argument("--refcat", required=True, help="Referencia catastral")
    parser.add_argument("--output", required=True, help="Ruta de salida del PDF")

    args = parser.parse_args()

    render_pdf(args.refcat, args.output)
