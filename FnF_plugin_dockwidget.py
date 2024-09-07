import os
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes, QgsFeatureRequest, QgsGeometry, QgsRectangle, QgsField, QgsFeature
from qgis.gui import QgsMapTool
from PyQt5.QtCore import pyqtSignal, QVariant, Qt
from PyQt5.QtGui import QCursor
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'FnF_plugin_dockwidget_base.ui'))

class PolygonSelectionMapTool(QgsMapTool):
    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.selected_feature = None
        self.setCursor(QCursor(Qt.CrossCursor))
    
    def canvasPressEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        layer = self.canvas.currentLayer()
        if layer and layer.isSpatial():
            request = QgsFeatureRequest().setFilterRect(self.canvas.extent())
            for feature in layer.getFeatures(request):
                if feature.geometry().contains(point):
                    self.selected_feature = feature
                    break
        if self.selected_feature:
            bbox = self.selected_feature.geometry().boundingBox()
            self.callback(bbox)
            self.canvas.unsetMapTool(self)

    def activate(self):
        self.selected_feature = None

class FnF_pluginDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(FnF_pluginDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.populate_comboboxes()
        self.createha.clicked.connect(self.createha_clicked)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def populate_comboboxes(self):
        """Populate the combo boxes with layers from the QGIS project."""
        # Get layers from the QGIS project
        layers = QgsProject.instance().mapLayers().values()
        
        # Populate the Point Data ComboBox
        self.comboBoxPointData.addItem("Selecteer waarnemingen")
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):  # Check if it's a vector layer
                if layer.geometryType() == QgsWkbTypes.PointGeometry:  # Check if it's a point layer
                    self.comboBoxPointData.addItem(layer.name(), layer.id())
        
        # Populate the Polygon Layer ComboBox
        self.comboBoxPolygonLayer.addItem("Selecteer gebiedslaag")
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):  # Check if it's a vector layer
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:  # Check if it's a polygon layer
                    self.comboBoxPolygonLayer.addItem(layer.name(), layer.id())

    def createha_clicked(self):
        # Get the selected polygon layer from the combo box
        selected_layer_id = self.comboBoxPolygonLayer.currentData()
        if not selected_layer_id:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a polygon layer.")
            return

        layer = QgsProject.instance().mapLayer(selected_layer_id)
        if not isinstance(layer, QgsVectorLayer) or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            QtWidgets.QMessageBox.warning(self, "Warning", "Selected layer is not a valid polygon layer.")
            return

        # Set the layer to the map tool and activate it
        canvas = iface.mapCanvas()
        tool = PolygonSelectionMapTool(canvas, self.create_grid_from_bbox)
        canvas.setMapTool(tool)
        print("Please click on a polygon to select it.")

    def create_grid_from_bbox(self, bbox):
        cell_size = 100  # 100x100 meter cells
        
        x_start, y_start = bbox.xMinimum(), bbox.yMinimum()
        x_end, y_end = bbox.xMaximum(), bbox.yMaximum()
        
        # Create a new vector layer for the grid
        grid_layer = QgsVectorLayer("Polygon?crs=EPSG:28992", "Grid", "memory")
        pr = grid_layer.dataProvider()
        
        # Add fields to the layer
        pr.addAttributes([QgsField("id", QVariant.Int)])
        grid_layer.updateFields()
        
        # Create a list to hold features
        features = []
        
        # Generate the grid
        x = x_start
        while x < x_end:
            y = y_start
            while y < y_end:
                # Create the geometry for each grid cell
                geom = QgsGeometry.fromRect(QgsRectangle(x, y, x + cell_size, y + cell_size))
                feature = QgsFeature()
                feature.setGeometry(geom)
                feature.setAttributes([len(features)])
                features.append(feature)
                y += cell_size
            x += cell_size
        
        # Add features to the grid layer
        pr.addFeatures(features)
        grid_layer.updateExtents()
        
        # Add the layer to the QGIS project
        QgsProject.instance().addMapLayer(grid_layer)
        QtWidgets.QMessageBox.information(self, "Success", "Grid created and added to the QGIS project.")
