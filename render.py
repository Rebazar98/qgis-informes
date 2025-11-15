from qgis.core import QgsApplication, QgsProject

def test_render():
    app = QgsApplication([], False)
    app.initQgis()

    project = QgsProject.instance()
    project.read('/app/proyecto.qgz')

    print("✅ Proyecto cargado correctamente")

    app.exitQgis()

if __name__ == "__main__":
    test_render()
