import os
import pandas as pd
from qgis.core import QgsProject, QgsVectorLayer, QgsFeatureRequest, QgsField

from .column_checker import load_column_settings

def filter_point_layer_with_request(point_layer):
    """Filter the point layer into 'Vogels' and 'Others' based on the species list."""
    species_settings_file = os.path.join(os.path.dirname(__file__), 'point_column_settings_file.txt')
    species_column_name = load_column_settings(species_settings_file).get('Soortnaam_NL')
    species_file_path = os.path.join(os.path.dirname(__file__), 'relation_tables', 'bij12_kwalificerendesoorten_fix.csv')

    try:
        species_list = pd.read_csv(species_file_path)
        print(f"Species list loaded successfully.")
    except Exception as e:
        print(f"Error loading species file: {e}")
        return None, None

    # Initialize empty lists for feature IDs
    feature_ids_vogels = []
    feature_ids_others = []

    # Filter features based on species
    for feature in point_layer.getFeatures():
        species_value = feature[species_column_name]
        matching_species = species_list[species_list['ned_naam'].str.lower() == species_value.lower()]

        if not matching_species.empty:
            if matching_species['ned_soortgroep'].values[0] == 'vogels':
                feature_ids_vogels.append(feature.id())
            else:
                feature_ids_others.append(feature.id())

    return feature_ids_vogels, feature_ids_others


def filter_point_layer_to_temp_layer(point_layer, add_to_map = True):
    """
    Filter the point layer and create two new layers: vogels_layer and others_layer
    based on the species list and add them to the QGIS map.
    """
    # Paths to settings and species data
    species_settings_file = os.path.join(os.path.dirname(__file__), 'point_column_settings_file.txt')
    species_column_name = load_column_settings(species_settings_file).get('Soortnaam_NL')
    group_column_name = load_column_settings(species_settings_file).get('ned_soortgroep')
    species_file_path = os.path.join(os.path.dirname(__file__), 'relation_tables', 'bij12_kwalificerendesoorten_fix.csv')

    # Load species list
    try:
        species_list = pd.read_csv(species_file_path)
        print(f"Species list loaded successfully.")
    except Exception as e:
        print(f"Error loading species file: {e}")
        return None, None

    # Filter features based on species
    feature_ids_vogels = []
    feature_ids_others = []

    for feature in point_layer.getFeatures():
        species_value = feature[species_column_name]
        matching_species = species_list[species_list['ned_naam'].str.lower() == species_value.lower()]


        if not matching_species.empty:
            if matching_species['ned_soortgroep'].values[0] == 'vogels':
                feature_ids_vogels.append(feature.id())
            else:
                feature_ids_others.append(feature.id())

    print(f"Vogels feature IDs: {feature_ids_vogels}")
    print(f"Others feature IDs: {feature_ids_others}")

    # Create filter strings directly from feature IDs
    if feature_ids_vogels:
        vogels_filter_string = f"\"{point_layer.fields()[0].name()}\" IN ({', '.join(map(str, feature_ids_vogels))})"
    else:
        vogels_filter_string = ""
        
    if feature_ids_others:
        others_filter_string = f"\"{point_layer.fields()[0].name()}\" IN ({', '.join(map(str, feature_ids_others))})"
    else:
        others_filter_string = ""

    print(f"Vogels filter string: {vogels_filter_string}")
    print(f"Others filter string: {others_filter_string}")

    # Create new layers based on the filtered feature IDs
    vogels_layer = QgsVectorLayer(point_layer.source(), 'Vogels Layer', point_layer.providerType())
    others_layer = QgsVectorLayer(point_layer.source(), 'Others Layer', point_layer.providerType())

    if not vogels_layer.isValid():
        print("Vogels layer is not valid!")
    if not others_layer.isValid():
        print("Others layer is not valid!")

    # Set subset strings if filter strings are not empty
    if vogels_filter_string:
        vogels_layer.setSubsetString(vogels_filter_string)
    if others_filter_string:
        others_layer.setSubsetString(others_filter_string)

    # Debug feature counts after applying subset string
    print(f"Number of features in Vogels layer after subset: {vogels_layer.featureCount()}")
    print(f"Number of features in Others layer after subset: {others_layer.featureCount()}")

    if add_to_map:
        # Add layers to QGIS project
        try:
            QgsProject.instance().addMapLayer(vogels_layer)
            QgsProject.instance().addMapLayer(others_layer)
            print("Layers added to QGIS project.")
        except Exception as e:
            print(f"Error adding layers to QGIS project: {e}")

    return vogels_layer, others_layer
