import os
import math
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes, QgsField, QgsFeature, QgsGeometry, QgsRectangle, QgsPointXY
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QVariant
from qgis.utils import iface
from .FnF_library.column_checker import check_columns, load_column_settings
from .FnF_library.fnf_kwaliteitsbepaling import fnf_kwaliteitsbepaling
from .FnF_library.create_ha_polygon_layer import get_bounding_box_from_selection, create_squares_from_bbox
from PyQt5 import QtCore
import datetime

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'FnF_plugin_dockwidget_base.ui'))

class FnF_pluginDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(FnF_pluginDockWidget, self).__init__(parent)
        self.setupUi(self)

        current_year = datetime.datetime.now().year
        six_years_ago = current_year - 6

        self.populate_comboboxes()
        self.createha.clicked.connect(self.createha_clicked)
        self.set_point_columns_button.clicked.connect(self.set_point_columns_clicked)
        self.set_polygon_columns_button.clicked.connect(self.set_polygon_columns_clicked)
        self.fnf_kwaliteitstoets_button.clicked.connect(self.fnf_kwaliteitstoets_clicked)
        self.totjaar.setText(str(current_year))
        self.beginjaar.setText(str(six_years_ago))

        QgsProject.instance().layersAdded.connect(self.update_comboboxes)
        QgsProject.instance().layerRemoved.connect(self.update_comboboxes)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        QgsProject.instance().layersAdded.disconnect(self.update_comboboxes)
        QgsProject.instance().layerRemoved.disconnect(self.update_comboboxes)
        event.accept()

    def populate_comboboxes(self):
        """Populate the combo boxes with layers from the QGIS project."""
        # Get the currently selected polygon layer
        current_grid_layer_id = self.comboBoxgridLayer.currentData()
        current_polygon_layer_id = self.comboBoxPolygonLayer.currentData()
        current_point_layer_id = self.comboBoxPointData.currentData()

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
        
        # Populate the Grid Layer ComboBox
        self.comboBoxgridLayer.clear()
        self.comboBoxgridLayer.addItem("Selecteer grid laag")
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):  # Check if it's a vector layer
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:  # Check if it's a polygon layer
                    self.comboBoxgridLayer.addItem(layer.name(), layer.id())
        
        # Restore the previously selected point layer
        if current_point_layer_id:
            point_index = self.comboBoxPointData.findData(current_point_layer_id)
            if point_index != -1:
                self.comboBoxPointData.setCurrentIndex(point_index)
        # Restore the previously selected polygon layer
        if current_polygon_layer_id:
            index = self.comboBoxPolygonLayer.findData(current_polygon_layer_id)
            if index != -1:
                self.comboBoxPolygonLayer.setCurrentIndex(index)
        
        # Restore the previously selected grid layer
        if current_grid_layer_id:
            index = self.comboBoxgridLayer.findData(current_polygon_layer_id)
            if index != -1:
                self.comboBoxgridLayer.setCurrentIndex(index)

    def update_comboboxes(self):
        """Update combo boxes when layers are added or removed."""
        self.populate_comboboxes()
    
    def set_columns(self, selected_layer_id, columnslayer):
        if not selected_layer_id:
            QtWidgets.QMessageBox.warning(self, "Warning", f"Please select a {columnslayer} layer.")
            return

        layer = QgsProject.instance().mapLayer(selected_layer_id)
        if not isinstance(layer, QgsVectorLayer):
            QtWidgets.QMessageBox.warning(self, "Warning", "Selected layer is not valid.")
            return
       
        # Check columns and save the selected columns
        check_columns(layer, columnslayer)

    def set_point_columns_clicked(self):
        """Handle the column checking and setting process."""
        selected_layer_id = self.comboBoxPointData.currentData()
        self.set_columns(selected_layer_id, 'point')

    def set_polygon_columns_clicked(self):
        """Handle the column checking and setting process."""
        selected_layer_id = self.comboBoxPolygonLayer.currentData()
        self.set_columns(selected_layer_id, 'polygon')

    def createha_clicked(self):
        selected_layer_id = self.comboBoxPolygonLayer.currentData()
        if not selected_layer_id:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a polygon layer.")
            return

        layer = QgsProject.instance().mapLayer(selected_layer_id)
        if not isinstance(layer, QgsVectorLayer) or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            QtWidgets.QMessageBox.warning(self, "Warning", "Selected layer is not a valid polygon layer.")
            return

        bbox = get_bounding_box_from_selection(layer)
        if not bbox:
            bbox = layer.extent()

        grid_layer = create_squares_from_bbox(bbox)
        QgsProject.instance().addMapLayer(grid_layer)

    def load_column_settings(self):
        """Load column settings from the saved file."""
        settings_file = os.path.join(os.path.dirname(__file__), 'column_settings.txt')
        return load_column_settings(settings_file)

    def fnf_kwaliteitstoets_clicked(self):
        # Get selected layer IDs from combo boxes
        grid_layer_id = self.comboBoxgridLayer.currentData()
        polygon_layer_id = self.comboBoxPolygonLayer.currentData()
        point_layer_id = self.comboBoxPointData.currentData()

        # Ensure all layers are selected
        if not (grid_layer_id and polygon_layer_id and point_layer_id):
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select grid, polygon, and point layers.")
            return

        # Retrieve the layers from their IDs
        grid_layer = QgsProject.instance().mapLayer(grid_layer_id)
        polygon_layer = QgsProject.instance().mapLayer(polygon_layer_id)
        point_layer = QgsProject.instance().mapLayer(point_layer_id)

        # Ensure valid layers
        if not (grid_layer and polygon_layer and point_layer):
            QtWidgets.QMessageBox.warning(self, "Warning", "One or more selected layers are not valid.")
            return

        # Run the external function, passing the actual layers
        fnf_kwaliteitsbepaling(grid_layer, polygon_layer, point_layer)
