import os
import pandas as pd
from .column_checker import load_column_settings
from qgis.core import (
    QgsSpatialIndex,
    QgsField,
    QgsVectorLayer,
    QgsFeature,
    QgsProject,
    edit
)
from qgis.PyQt.QtCore import QVariant


def load_species_list():
    """Load the species list CSV."""
    species_file_path = os.path.join(os.path.dirname(__file__), 'relation_tables', 'bij12_kwalificerendesoorten_fix.csv')
    return pd.read_csv(species_file_path)


def load_column_settings_files():
    """Load the column settings for both point and polygon layers."""
    species_settings_file = os.path.join(os.path.dirname(__file__), 'point_column_settings_file.txt')
    polygon_settings_file = os.path.join(os.path.dirname(__file__), 'polygon_column_settings_file.txt')

    species_column_name = load_column_settings(species_settings_file)['Soortnaam_NL']
    polygon_beheertype_name = load_column_settings(polygon_settings_file)['BeheerType']

    return species_column_name, polygon_beheertype_name


def get_intersecting_and_neighboring_cells(grid_layer, polygon_layer, polygon_beheertype_name):
    """
    Identify grid cells that intersect with polygons, and add nearby cells using a buffer.
    Returns a dictionary of grid cell IDs mapped to beheertype values and a set of grid cell IDs to include.
    """
    # Create a spatial index for the grid layer
    spatial_index = QgsSpatialIndex(grid_layer.getFeatures())

    # Dictionary to hold the beheertypen lists for each grid feature
    beheertypen_dict = {feature.id(): [] for feature in grid_layer.getFeatures()}
    grid_cells_to_include = set()

    # Iterate over polygon features
    for polygon_feature in polygon_layer.getFeatures():
        polygon_geom = polygon_feature.geometry()
        beheertype_value = polygon_feature[polygon_beheertype_name]  # Get the beheertypen value

        # Get grid cells that intersect with the polygon
        intersecting_ids = spatial_index.intersects(polygon_geom.boundingBox())

        for grid_id in intersecting_ids:
            grid_feature = grid_layer.getFeature(grid_id)
            grid_geom = grid_feature.geometry()

            if grid_geom.intersects(polygon_geom):
                grid_cells_to_include.add(grid_id)
                beheertypen_dict[grid_id].append(beheertype_value)

                # Add neighboring cells using a buffer
                buffer_geom = grid_geom.buffer(0.001, 1)
                nearby_ids = spatial_index.intersects(buffer_geom.boundingBox())
                grid_cells_to_include.update(nearby_ids)

    return beheertypen_dict, grid_cells_to_include


def create_aggregated_layer(grid_layer, beheertypen_dict, grid_cells_to_include):
    """
    Create a new memory layer to store aggregated beheertype values and add it to the QGIS project.
    """
    # Create a new memory layer
    new_layer = QgsVectorLayer(f'Polygon?crs={grid_layer.crs().authid()}', 'Overlappende_gridcellen', 'memory')
    new_layer_data = new_layer.dataProvider()

    # Add fields from the grid layer and a new field for aggregated beheertype values
    new_layer_data.addAttributes(grid_layer.fields())
    new_layer.updateFields()

    # Add features to the new layer
    with edit(new_layer):
        for grid_id in grid_cells_to_include:
            grid_feature = grid_layer.getFeature(grid_id)
            new_feature = QgsFeature(new_layer.fields())

            new_feature.setGeometry(grid_feature.geometry())
            new_feature.setAttributes(grid_feature.attributes())

            beheertypen_list = beheertypen_dict.get(grid_id, [])
            if beheertypen_list:
                beheertypen_str = ', '.join(beheertypen_list)

            new_layer_data.addFeature(new_feature)

    # Add the new layer to the QGIS project
    QgsProject.instance().addMapLayer(new_layer)
    return new_layer
    
def fnf_kwaliteitsbepaling(grid_layer, polygon_layer, point_layer):
    """Main function to run the kwaliteitsbepaling process."""
    #Load data and column settings
    species_list = load_species_list()
    species_column_name, polygon_beheertype_name = load_column_settings_files()

    #Clear previous selections in the grid layer
    grid_layer.removeSelection()

    #Get intersecting and neighboring grid cells
    beheertypen_dict, grid_cells_to_include = get_intersecting_and_neighboring_cells(grid_layer, polygon_layer, polygon_beheertype_name)

    #Create the aggregated beheertypen layer and add it to the project
    create_aggregated_layer(grid_layer, beheertypen_dict, grid_cells_to_include)
    
