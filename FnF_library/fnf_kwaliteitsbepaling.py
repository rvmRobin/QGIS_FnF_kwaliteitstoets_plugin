def fnf_kwaliteitsbepaling(grid_layer, polygon_layer, point_layer):
    import os
    import pandas as pd
    from .column_checker import load_column_settings

    # Load CSV and Excel files into DataFrames
    species_list = pd.read_csv(os.path.join(os.path.dirname(__file__), 'relation_tables', 'soortenlijst_NDFF.csv'))
    species_list_spiecies_column = 'Nederlandse naam'
    score_species = pd.read_excel(os.path.join(os.path.dirname(__file__), 'relation_tables', 'Bij12_Kwalificerende_soorten_per_beheertype.xlsx'))
    score_species_spiecies_column = 'Ned_naam_NDFF'

    # Load column settings from the file
    settings_file = os.path.join(os.path.dirname(__file__), 'column_settings_file.txt')
    column_name = load_column_settings(settings_file)['Soortnaam_NL']
