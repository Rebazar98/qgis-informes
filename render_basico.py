from qgis.core import QgsApplication, QgsProject

# Iniciar QGIS en modo sin interfaz
app = QgsApplication([], False)
app.initQgis()

# Intentar cargar el proyecto
project = QgsProject.instance()
success = project.read('/app/proyecto.qgz')

if success:
    print("✅ Proyecto cargado correctamente.")
else:
    print("❌ Error al cargar el proyecto.")

# Finalizar QGIS
app.exitQgis()

