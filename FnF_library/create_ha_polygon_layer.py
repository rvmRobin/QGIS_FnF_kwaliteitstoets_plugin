import math
from qgis.core import QgsRectangle, QgsVectorLayer, QgsFeature, QgsGeometry, QgsField
from qgis.PyQt.QtCore import QVariant

CELL_SIZE = 100  # 100x100 meter cells

def get_bounding_box_from_selection(layer):
    """Get the bounding box of the selected features in the layer."""
    selection = layer.selectedFeatures()
    if not selection:
        return None

    extent = QgsRectangle()
    for feature in selection:
        extent.combineExtentWith(feature.geometry().boundingBox())
    
    return extent

def create_squares_from_bbox(bbox, crs="EPSG:28992"):
    """Create a grid of square cells from a bounding box."""
    x_min = math.floor(bbox.xMinimum() / CELL_SIZE) * CELL_SIZE - 100
    y_min = math.floor(bbox.yMinimum() / CELL_SIZE) * CELL_SIZE - 100
    x_max = math.ceil(bbox.xMaximum() / CELL_SIZE) * CELL_SIZE + 100
    y_max = math.ceil(bbox.yMaximum() / CELL_SIZE) * CELL_SIZE + 100
    
    # Create a new vector layer for the grid
    grid_layer = QgsVectorLayer(f"Polygon?crs={crs}", "Square Grid", "memory")
    pr = grid_layer.dataProvider()
    
    # Add fields to the layer
    pr.addAttributes([QgsField("id", QVariant.String)])
    grid_layer.updateFields()
    
    features = []
    x = x_min
    while x < x_max:
        y = y_min
        while y < y_max:
            square_geom = QgsGeometry.fromRect(QgsRectangle(x, y, x + CELL_SIZE, y + CELL_SIZE))
            feature = QgsFeature()
            feature.setGeometry(square_geom)
            # Set the ID to the coordinates of the bottom-left corner of the square
            feature.setAttributes([f"{x}-{y}"])
            features.append(feature)
            y += CELL_SIZE
        x += CELL_SIZE
    
    pr.addFeatures(features)
    grid_layer.updateExtents()
    
    return grid_layer
