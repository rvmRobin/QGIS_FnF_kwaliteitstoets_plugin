import os
import pandas as pd
from qgis.core import (
    QgsSpatialIndex,
    QgsField,
    QgsVectorLayer,
    QgsFeature,
    QgsProject,
    edit,
    QgsProcessingFeatureSourceDefinition,
    QgsApplication,
    QgsTask,
    QgsMessageLog,
    Qgis,
)
from qgis.analysis import QgsNativeAlgorithms
from PyQt5.QtCore import QVariant
import processing
from .column_checker import load_column_settings


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


def spatial_join_two_layers(target_layer, join_layer, joining_fields):
    """
    Perform a spatial join between two QGIS vector layers using 'native:joinattributesbylocation'.
    """
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

    if not target_layer or not join_layer:
        raise ValueError("One or both input layers are invalid.")

    params = {
        'INPUT': QgsProcessingFeatureSourceDefinition(
            target_layer.id(),
            selectedFeaturesOnly=False,
        ),
        'JOIN': QgsProcessingFeatureSourceDefinition(
            join_layer.id(),
            selectedFeaturesOnly=False,
        ),
        'PREDICATE': [0],
        'JOIN_FIELDS': joining_fields,
        'METHOD': 0,
        'DISCARD_NONMATCHING': False,
        'OUTPUT': 'memory:',
    }

    result = processing.run("native:joinattributesbylocation", params)
    return result


def vectorlayer_to_df(vectorlayer):
    """Convert a QGIS vector layer to a pandas DataFrame."""
    if not vectorlayer.isValid():
        raise ValueError("Invalid vector layer.")
    fields = [field.name() for field in vectorlayer.fields()]
    data = [{field: feature[field] for field in fields} for feature in vectorlayer.getFeatures()]
    return pd.DataFrame(data)


def pd_aggr_layer(df_layer_to_aggr, aggr_expression):
    """Aggregate a DataFrame using a given aggregation expression."""
    return df_layer_to_aggr.groupby('id').agg(aggr_expression).reset_index()


def df_to_project(df, layer_name):
    """Add a pandas DataFrame as a layer to the QGIS project."""
    layer = QgsVectorLayer("None", layer_name, "memory")
    provider = layer.dataProvider()

    fields = [QgsField(name, QVariant.String) for name in df.columns]
    provider.addAttributes(fields)
    layer.updateFields()

    for _, row in df.iterrows():
        feature = QgsFeature()
        feature.setAttributes([str(value) for value in row.values])
        provider.addFeature(feature)

    QgsProject.instance().addMapLayer(layer)


def process_and_add_to_project(join_result, aggregation_rules, layer_name, to_project = True):
    """Process join results and add them as a layer to the project."""
    if 'OUTPUT' not in join_result:
        raise ValueError("Join result does not contain 'OUTPUT'.")

    join_output = join_result['OUTPUT']
    df_layer = vectorlayer_to_df(join_output)
    aggregated_df = pd_aggr_layer(df_layer, aggregation_rules)
    if to_project:
        df_to_project(aggregated_df, layer_name)
    return aggregated_df


class JoinAndProcessTask(QgsTask):
    def __init__(self, grid_layer, polygon_layer, point_layer, polygon_rules, point_rules):
        super().__init__("Join and Process Layers")
        self.grid_layer = grid_layer
        self.polygon_layer = polygon_layer
        self.point_layer = point_layer
        self.polygon_rules = polygon_rules
        self.point_rules = point_rules

    def run(self):
        try:
            grid_polygon_join = spatial_join_two_layers(
                self.grid_layer, self.polygon_layer, list(self.polygon_rules.keys())
            )
            grid_point_join = spatial_join_two_layers(
                self.grid_layer, self.point_layer, list(self.point_rules.keys())
            )

            aggr_df_grid_polygon = process_and_add_to_project(
                grid_polygon_join,
                self.polygon_rules,
                "Grid_beheertypen_lijst",
                to_project = False
            )

            aggr_df_grid_point = process_and_add_to_project(
                grid_point_join,
                self.point_rules,
                "Grid_point_lijst",
                to_project = False
            )

            # Merge the processed DataFrames on 'id'
            merged_df = pd.merge(
                aggr_df_grid_polygon,
                aggr_df_grid_point,
                on="id",
                how="outer"  # Use 'outer' to include all records
            )

            # Add the merged DataFrame to the QGIS project
            df_to_project(merged_df, "Grid_Combined")

            return True
        except Exception as e:
            QgsMessageLog.logMessage(f"Error during task execution: {e}", level=Qgis.Critical)
            return False

    def finished(self, result):
        if result:
            QgsMessageLog.logMessage("Task completed successfully!", level=Qgis.Info)
        else:
            QgsMessageLog.logMessage("Task failed!", level=Qgis.Warning)


def fnf_kwaliteitsbepaling(grid_layer, polygon_layer, point_layer):
    """Run the kwaliteitsbepaling process in a background task."""
    species_list = load_species_list()
    species_column_name, polygon_beheertype_name, polygon_gebied_name = load_column_settings_files()

    polygon_rules = {
        'beheerType': lambda x: list(set(x.dropna())),
        'Gebied': lambda x: list(set(x.dropna()))
    }
    point_rules = {
        'Soortnaam_NL': lambda x: list(set(x.dropna()))
    }

    grid_layer.removeSelection()

    task = JoinAndProcessTask(grid_layer, polygon_layer, point_layer, polygon_rules, point_rules)
    QgsApplication.taskManager().addTask(task)
