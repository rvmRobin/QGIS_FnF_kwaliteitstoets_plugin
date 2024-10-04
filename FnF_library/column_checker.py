import os
from qgis.PyQt import QtWidgets
from qgis.core import QgsVectorLayer

class ColumnSelectionDialog(QtWidgets.QDialog):
    def __init__(self, required_columns, field_names, current_mapping, parent=None):
        super(ColumnSelectionDialog, self).__init__(parent)
        self.setWindowTitle("Select Columns for Required Fields")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.combo_boxes = {}
        for required_col in required_columns:
            label = QtWidgets.QLabel(f"Select column for {required_col}:")
            combo_box = QtWidgets.QComboBox()
            combo_box.addItems(field_names)
            
            # Set the current selection based on the saved mapping, if it exists
            if required_col in current_mapping:
                index = combo_box.findText(current_mapping[required_col])
                if index >= 0:
                    combo_box.setCurrentIndex(index)
            
            self.combo_boxes[required_col] = combo_box
            self.layout.addWidget(label)
            self.layout.addWidget(combo_box)

        # Add buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def get_selected_columns(self):
        return {col: self.combo_boxes[col].currentText() for col in self.combo_boxes}

def load_required_columns(settings_file):
    """Load required columns from the first column of the settings file."""
    required_columns = []
    with open(settings_file, 'r') as file:
        for line in file:
            if line.strip():  # Ensure the line is not empty
                # Split the line by the semicolon and append the first element
                required_columns.append(line.split(';')[0].strip())  # Strip to remove any leading/trailing whitespace
    return required_columns


def check_columns(layer: QgsVectorLayer, columnslayer):
    """Check columns in the layer and always allow the user to reselect them."""
    settings_file = os.path.join(os.path.dirname(__file__), f'{columnslayer}_column_settings_file.txt')
    required_columns = load_required_columns(settings_file)

    # Get current fields from the layer
    fields = layer.fields()
    field_names = [field.name() for field in fields]
    
    # Load saved column settings
    saved_columns = load_column_settings(settings_file)

    # Always allow user to reselect columns, even if saved columns match
    dialog = ColumnSelectionDialog(required_columns, field_names, saved_columns)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        selected_columns = dialog.get_selected_columns()

        # Update only the selected columns in the saved settings
        saved_columns.update(selected_columns)

        # Save the updated settings back to the file
        save_column_settings(settings_file, saved_columns)

        # Optionally, show a message that the settings were updated
        QtWidgets.QMessageBox.information(None, "Information", "Column settings have been updated.")

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

def save_column_settings(settings_file: str, column_mapping: dict):
    """Save the column settings to the file."""
    with open(settings_file, 'w') as f:
        for key, value in column_mapping.items():
            f.write(f"{key};{value}\n")