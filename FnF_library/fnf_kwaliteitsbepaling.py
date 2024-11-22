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
## CLEAN THIS
from qgis.core import (
    QgsProcessing,
    QgsProcessingFeatureSourceDefinition,
    QgsProject,
    QgsApplication,
)
from qgis.analysis import QgsNativeAlgorithms
import processing


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
    polygon_gebied_name = load_column_settings(polygon_settings_file)['Gebied']

    return species_column_name, polygon_beheertype_name, polygon_gebied_name

def spatial_join_two_layers(target_layer, join_layer, polygon_beheertype_name, polygon_gebied_name):
    """
    Perform a spatial join between two QGIS vector layers using 'native:joinattributesbylocation'.

    Parameters:
    target_layer (QgsVectorLayer): The layer that receives attributes.
    join_layer (QgsVectorLayer): The layer that provides attributes.

    Returns:
    QgsVectorLayer or None: The resulting joined layer, or None if the operation fails.
    """
    # Ensure the processing algorithms are registered
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    # Validate input layers
    if not target_layer or not join_layer:
        print("Error: One or both input layers are invalid.")
        return None

    # Define parameters for the spatial join
    params = {
        'INPUT': QgsProcessingFeatureSourceDefinition(
            target_layer.id(),  # Target layer
            selectedFeaturesOnly=False,
        ),
        'JOIN': QgsProcessingFeatureSourceDefinition(
            join_layer.id(),  # Join layer
            selectedFeaturesOnly=False,
        ),
        'PREDICATE': [0], # Spatial predicate
        'JOIN_FIELDS': [polygon_beheertype_name, polygon_gebied_name], # Joining fields
        'METHOD': 0, # Create a new layer
        'DISCARD_NONMATCHING': False, # Keep non-matching features
        'OUTPUT': 'memory:' # Store result in memory
    }

    try:
        # Run the processing algorithm
        result = processing.run("native:joinattributesbylocation", params)
        return result

    except Exception as e:
        print(f"An error occurred during the spatial join: {e}")
        return None

def aggr_joined_layer(joined_layer, polygon_beheertype_name, polygon_gebied_name):
    params={
        'INPUT': joined_layer,
        'GROUP_BY':'id',
        'AGGREGATES':[{'aggregate': 'concatenate','delimiter': ',','input': polygon_beheertype_name,'length': 0,'name': 'polygon_beheertype_name','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},
                        {'aggregate': 'concatenate','delimiter': ',','input': polygon_gebied_name,'length': 0,'name': 'polygon_gebied_name','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'}],
        'OUTPUT':'memory:'} # Store result in memory
    
    try:
        # Run the aggregate algorithm
        aggr_result = processing.run("native:aggregate", params)
        return aggr_result

    except Exception as e:
        print(f"An error occurred during the spatial join: {e}")
        return None

def vectorlayer_to_df(vectorlayer):
    if not vectorlayer.isValid():
        raise ValueError("Invalid vectorlayer for vactorlayer to df")
    else:
        fields = [field.name() for field in vectorlayer.fields()]
        data = [{field: feature[field] for field in fields} for feature in vectorlayer.getFeatures()]
        df_layer = pd.DataFrame(data)
        print(df_layer)
        return df_layer

def pd_aggr_layer(df_layer_to_aggr):
    #df_layer_to_aggr.groupby('id')['BeheerType', 'Gebied'].apply(lambda x: ','.join(x)).reset_index()
    df_layer = df_layer_to_aggr.groupby('id').agg({'beheerType': lambda x: list(x), 'Gebied': lambda x: list(x)}).reset_index()
    #df_layer = df_layer[df_layer['beheerType'].notna()] # All grid with beheertype
    df_layer = df_layer[df_layer['beheerType'].apply(lambda x: x[0] is not None)]
    df_layer['beheerType'] = [list(set(x)) for x in df_layer['beheerType']]
    df_layer['Gebied'] = [list(set(x)) for x in  df_layer['Gebied']]

    print(df_layer)
    return df_layer

def df_to_project(df):
    # Create an in-memory layer
    layer = QgsVectorLayer("None", "Grid_beheertypen_lijst", "memory")
    provider = layer.dataProvider()

    # Add fields to the layer
    fields = [QgsField(name, QVariant.String) for name in df.columns]
    provider.addAttributes(fields)
    layer.updateFields()

    # Add rows as features
    for _, row in df.iterrows():
        feature = QgsFeature()
        # Ensure all row values are converted to strings
        feature.setAttributes([str(value) for value in row.values])
        provider.addFeature(feature)

    # Add the layer to the QGIS project
    QgsProject.instance().addMapLayer(layer)

    print("Layer added successfully!")

def fnf_kwaliteitsbepaling(grid_layer, polygon_layer, point_layer):
    """Main function to run the kwaliteitsbepaling process."""
    #Load data and column settings
    species_list = load_species_list()
    species_column_name, polygon_beheertype_name, polygon_gebied_name = load_column_settings_files()

    #Clear previous selections in the grid layer
    grid_layer.removeSelection()

    grid_polygon_join = spatial_join_two_layers(grid_layer, polygon_layer, polygon_beheertype_name, polygon_gebied_name)
     # Check if the result was created
    if 'OUTPUT' in grid_polygon_join:
        grid_polygon_join_output = grid_polygon_join['OUTPUT']
        
        df_grid_polygon_join = vectorlayer_to_df(grid_polygon_join_output)
        aggr_df_grid_polygon = pd_aggr_layer(df_grid_polygon_join)
        df_to_project(aggr_df_grid_polygon)
        
        #aggr_grid = aggr_joined_layer(grid_polygon_join_output, polygon_beheertype_name, polygon_gebied_name)
        #if 'OUTPUT' in aggr_grid:
        #    aggr_grid_output = aggr_grid['OUTPUT']
        #    QgsProject.instance().addMapLayer(aggr_grid_output)
        #    print("Spatial join and aggregate completed. Result added to the map.")
        #else:
        #    print("Error: aggragate did not produce a valid output.")
        #    return None
    else:
        print("Error: Spatial join did not produce a valid output.")
        return None
