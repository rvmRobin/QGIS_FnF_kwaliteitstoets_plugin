import os
from qgis.PyQt import QtWidgets
from qgis.core import QgsVectorLayer

def check_columns(layer: QgsVectorLayer, required_columns: list):
    """Check if required columns exist in the layer, if not, prompt the user to select them."""
    settings_file = os.path.join(os.path.dirname(__file__), 'column_settings_file.txt')

    fields = layer.fields()
    missing_columns = [col for col in required_columns if col not in fields.names()]

    # If all required columns are present, return
    if not missing_columns:
        return

    # Ask the user to select the missing columns
    selected_columns = {}
    for missing_col in missing_columns:
        field_names = [field.name() for field in fields]
        item, ok = QtWidgets.QInputDialog.getItem(None, "Select Column", f"Select column for {missing_col}:", field_names, 0, False)
        if ok and item:
            selected_columns[missing_col] = item

    # Save the selected columns to a file
    with open(settings_file, 'w') as f:
        for key, value in selected_columns.items():
            f.write(f"{key};{value}\n")

def load_column_settings(settings_file: str):
    """Load saved column settings from a file."""
    if not os.path.exists(settings_file):
        return {}

    column_mapping = {}
    with open(settings_file, 'r') as f:
        for line in f:
            key, value = line.strip().split(';')
            column_mapping[key] = value
    return column_mapping
