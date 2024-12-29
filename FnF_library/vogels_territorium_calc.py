import os
import pandas as pd
from .column_checker import load_column_settings

def get_neighbors(grid_id):
    x, y = map(int, grid_id.split("-"))
    neighbors = [
        f"{x - 100}-{y - 100}", f"{x}-{y - 100}", f"{x + 100}-{y - 100}",
        f"{x - 100}-{y}", f"{x}-{y}", f"{x + 100}-{y}",
        f"{x - 100}-{y + 100}", f"{x}-{y + 100}", f"{x + 100}-{y + 100}"
    ]
    return neighbors

def vogels_territorium(layer): 
    species_path = os.path.join(os.path.dirname(__file__), 'relation_tables/soortenlijst_NDFF.csv')
    species_df = pd.read_csv(species_path, delimiter = ';')

    species_settings_file = os.path.join(os.path.dirname(__file__), 'point_column_settings_file.txt')
    species_column_name = load_column_settings(species_settings_file)['Soortnaam_NL']

    vogels_list = species_df[species_df['ned_soortgroep'] == 'vogels']['ned_naam'].tolist()
    vogels_list = [x.lower() for x in vogels_list]
    vogels_ids = layer[layer['Soortnaam_NL'].apply(lambda x: isinstance(x, list) and any(vogel.lower() in [species.lower() for species in x] for vogel in vogels_list))]['id']
    
    # Dictionary for storing values
    values_to_add = {'id': [],
                    'vogels_territorium': []}

    # Loop over the grid cells with bird species
    for grid_id in vogels_ids:
        # Get the species list from the layer
        toevoegen_soorten = layer.loc[layer['id'] == grid_id, species_column_name].values[0]
        toevoegen_soorten = [x.lower() for x in toevoegen_soorten]
        toevoegen_soorten = [item for item in toevoegen_soorten if item in [vogel.lower() for vogel in vogels_list]]

        # Get the neighbors for the current grid cell
        neighbors = get_neighbors(grid_id)
        
        # For each neighbor, add the species to the values_to_add dictionary
        for neighbor in neighbors:
            values_to_add['id'].append(neighbor)
            values_to_add['vogels_territorium'].append(toevoegen_soorten)

    # Now aggregate values: ensure unique ids and no duplicate species
    aggregated_values_to_add = {'id': [], 'vogels_territorium': []}
    # Loop through the collected values and aggregate species
    for idx, id_value in enumerate(values_to_add['id']):
        if id_value not in aggregated_values_to_add['id']:
            aggregated_values_to_add['id'].append(id_value)
            # Aggregate species for the corresponding ID
            species_for_id = set()
            for i in range(len(values_to_add['id'])):
                if values_to_add['id'][i] == id_value:
                    species_for_id.update(values_to_add['vogels_territorium'][i])  # Add species without duplicates
            aggregated_values_to_add['vogels_territorium'].append(list(species_for_id))  # Convert back to list
    return pd.DataFrame(aggregated_values_to_add)