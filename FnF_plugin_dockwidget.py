import os
import math
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes, QgsField, QgsFeature, QgsGeometry, QgsRectangle, QgsPointXY
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QVariant
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'FnF_plugin_dockwidget_base.ui'))

class FnF_pluginDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(FnF_pluginDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.populate_comboboxes()
        self.createha.clicked.connect(self.createha_clicked)

        QgsProject.instance().layersAdded.connect(self.update_comboboxes)
        QgsProject.instance().layerRemoved.connect(self.update_comboboxes)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        QgsProject.instance().layersAdded.disconnect(self.update_comboboxes)
        QgsProject.instance().layerRemoved.disconnect(self.update_comboboxes)
        event.accept()

    def populate_comboboxes(self):
        """Populate the combo boxes with layers from the QGIS project."""
        # Get layers from the QGIS project
        layers = QgsProject.instance().mapLayers().values()
        
        # Populate the Point Data ComboBox
        self.comboBoxPointData.clear()
        self.comboBoxPointData.addItem("Selecteer waarnemingen")
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):  # Check if it's a vector layer
                if layer.geometryType() == QgsWkbTypes.PointGeometry:  # Check if it's a point layer
                    self.comboBoxPointData.addItem(layer.name(), layer.id())
        
        # Populate the Polygon Layer ComboBox
        self.comboBoxPolygonLayer.clear()
        self.comboBoxPolygonLayer.addItem("Selecteer gebiedslaag")
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):  # Check if it's a vector layer
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:  # Check if it's a polygon layer
                    self.comboBoxPolygonLayer.addItem(layer.name(), layer.id())
    
    def update_comboboxes(self):
        """Update combo boxes when layers are added or removed."""
        self.populate_comboboxes()

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

        # Get the bounding box from the selected polygons
        bbox = self.get_bounding_box_from_selection(layer)
        
        if not bbox:
            # If no polygons are selected, use the bounding box of the entire layer
            bbox = layer.extent()
        
        self.create_squares_from_bbox(bbox)

    def get_bounding_box_from_selection(self, layer):
        """Get the bounding box of the selected features in the layer."""
        selection = layer.selectedFeatures()
        if not selection:
            return None

        extent = QgsRectangle()
        for feature in selection:
            extent.combineExtentWith(feature.geometry().boundingBox())

        return extent

    def create_squares_from_bbox(self, bbox):
        cell_size = 100  # 100x100 meter cells
        
        # Round bounding box coordinates to nearest 100 meters
        x_min = math.floor(bbox.xMinimum() / cell_size) * cell_size - 100
        y_min = math.floor(bbox.yMinimum() / cell_size) * cell_size - 100
        x_max = math.ceil(bbox.xMaximum() / cell_size) * cell_size + 100
        y_max = math.ceil(bbox.yMaximum() / cell_size) * cell_size + 100
        
        # Create a new vector layer for the grid
        grid_layer = QgsVectorLayer("Polygon?crs=EPSG:28992", "Square Grid", "memory")
        pr = grid_layer.dataProvider()
        
        # Add fields to the layer
        pr.addAttributes([QgsField("id", QVariant.Int)])
        grid_layer.updateFields()
        
        # Create a list to hold features
        features = []
        
        # Generate the grid
        x = x_min
        while x < x_max:
            y = y_min
            while y < y_max:
                # Create the geometry for each square cell
                square_geom = QgsGeometry.fromRect(QgsRectangle(x, y, x + cell_size, y + cell_size))
                feature = QgsFeature()
                feature.setGeometry(square_geom)
                feature.setAttributes([len(features)])
                features.append(feature)
                y += cell_size
            x += cell_size
        
        # Add features to the grid layer
        pr.addFeatures(features)
        grid_layer.updateExtents()
        
        # Add the layer to the QGIS project
        QgsProject.instance().addMapLayer(grid_layer)