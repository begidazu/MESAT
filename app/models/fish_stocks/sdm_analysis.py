import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Sequence, Union
import pyproj
import rasterio
import numpy as np
import pandas as pd

class SDMFileManager:
    """
    Advanced SDM (Species Distribution Models) file manager that parses filenames with key=value format.
    
    This class provides a convenient interface to access SDM result files organized in a hierarchical
    folder structure based on the MPAEU results structure. It automatically indexes all files and allows 
    retrieval based on various parameters such as taxon ID, model type, scenario, metrics, etc.
    
    Folder Structure:
        results_wd/
        └── SDMs/
            ├── taxonid=126421/
            │   └── model=mpaeu/
            │       ├── figures/
            │       ├── metrics/
            │       ├── models/
            │       └── predictions/
            ├── taxonid=126426/
            └── taxonid=126822/
    
    Available Parameters by Folder Type:
    
    'figures':
        - taxonid: Species identifier (e.g., '126421')
        - model: Model type (e.g., 'mpaeu')
        - method: Algorithm (e.g., 'maxent', 'rf', 'xgboost', 'ensemble')
        - what: Type of figure (e.g., 'responsecurves', 'shape')
        - classification_ds_what: Alternative parameter for classification datasets
    
    'metrics':
        - taxonid: Species identifier
        - model: Model type
        - method: Algorithm (e.g., 'ensemble', 'maxent', 'rf', 'xgboost') [OPTIONAL - not present for some metrics]
        - what: Metric type (e.g., 'cvmetrics', 'fullmetrics', 'respcurves', 'varimportance', 
                  'biasmetrics', 'posteval', 'thresholds')
        - classification_ds_what: Alternative parameter
        
        NOTE: Some metrics files (biasmetrics, posteval, thresholds) don't have a 'method' parameter.
              You can search for them without specifying method:
                  manager.get_file(taxon_id='126421', folder_type='metrics', what='thresholds')
    
    'models':
        - taxonid: Species identifier
        - model: Model type
        - method: Algorithm
        - what: 'model' (the trained model object)
        - classification_ds_what: Alternative parameter
    
    'predictions':
        - taxonid: Species identifier
        - model: Model type
        - method: Algorithm
        - scen: Scenario or time period (e.g., '1990_2000', '2000_2010', '2010_2020', '2020_2024',
                 'current', 'ssp126_dec50', 'ssp126_dec100', 'ssp245_dec50', 'ssp245_dec100',
                 'ssp370_dec50', 'ssp370_dec100', 'ssp460_dec50', 'ssp460_dec100',
                 'ssp585_dec50', 'ssp585_dec100')
        - what: Prediction type (e.g., 'mess', 'shape')
        - classification_ds_scen: Alternative parameter
    
    Example Usage:
        # Initialize the manager
        manager = SDMFileManager(r'C:\path\to\SDMs')
        
        # Get a specific predictions file
        file_path = manager.get_file(
            taxon_id='126421',
            folder_type='predictions',
            method='ensemble',
            scen='ssp585_dec100'
        )
        
        # Get all metrics for a specific method
        files = manager.get_files(
            taxon_id='126421',
            folder_type='metrics',
            method='ensemble'
        )
        
        # Get thresholds (no method parameter required)
        thresholds = manager.get_file(
            taxon_id='126421',
            folder_type='metrics',
            what='thresholds'
        )
        
        # List available parameters for a folder type
        params = manager.list_parameters('126421', 'predictions')
        
        # Print usage examples
        manager.print_usage_examples('126421')
    """
    
    def __init__(self, sdm_root: str):
        """
        Initialize the SDM file manager.
        
        Args:
            sdm_root (str): Path to the 'SDMs' root directory containing all species folders.
                           Example: r'C:\path\to\Results\SDMs'
        
        Raises:
            FileNotFoundError: If the sdm_root directory does not exist.
        """
        self.sdm_root = Path(sdm_root)
        self.file_index = self._build_file_index()
    
    def _build_file_index(self) -> Dict:
        """
        Constructs an index of all files organized by taxon_id, folder_type, and parameters extracted from filenames.
        """
        index = {}
        
        # Iterate over species (e.g., taxonid=126421)
        for species_folder in self.sdm_root.iterdir():
            if not species_folder.is_dir():
                continue
            
            # Extract the taxon_id from the folder (taxonid=126421 -> 126421)
            taxon_id = self._extract_param_value(species_folder.name, 'taxonid')
            index[taxon_id] = {}
            
            # Iterate over model_folders (e.g., model=mpaeu)
            for model_folder in species_folder.iterdir():
                if not model_folder.is_dir():
                    continue
                
                # Iterate over folder types (figures, metrics, model, predictions)
                for type_folder in model_folder.iterdir():
                    if not type_folder.is_dir():
                        continue
                    
                    folder_type = type_folder.name  # 'figures', 'metrics', etc.
                    
                    if folder_type not in index[taxon_id]:
                        index[taxon_id][folder_type] = []
                    
                    # Iterate over files in each type folder
                    for file in type_folder.iterdir():
                        if file.is_file():
                            # Parse the filename
                            params = self._parse_filename(file.name)
                            
                            # Store file information
                            file_info = {
                                'path': str(file),
                                'filename': file.name,
                                'extension': file.suffix,
                                'params': params
                            }
                            
                            index[taxon_id][folder_type].append(file_info)
        
        return index
    
    def _extract_param_value(self, text: str, param_name: str) -> Optional[str]:
        """
        Extracts the value of a specific parameter from a text.
        
        Example: 'taxonid=126421' with param_name='taxonid' -> '126421'
                 'scen=1990_2000' with param_name='scen' -> '1990_2000'
        """
        # Pattern that captures values with underscores (e.g., 1990_2000)
        # Stops before the next parameter (which starts with _[word]=)
        pattern = rf'{param_name}=([0-9a-z_]+?)(?=_[a-z_]+(?:=|$)|$)'
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip('[]')
            return value
        return None
    
    def _parse_filename(self, filename: str) -> Dict[str, Any]:
        """
        Extracts parameters from the filename.

        Supports formats:
        - taxonid=[12642]_model=mpaeu_method=ensemble_what=cvmetrics.parquet
        - taxonid=[12642]_model=mpaeu_method=ensemble_scen=1990_2000_cog.tif
        
        Returns:
            Dictionary with the extracted parameters
        """
        params = {}
        
        # Remove the extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Search for all key-value pairs
        # Pattern: _key=value or key=value at the beginning
        # Captures values with underscores (e.g., 1990_2000) and stops before:
        # - The next parameter (_key=)
        # - A suffix (_cog, _tif, etc.)
        # - The end of the string
        pattern = r'(?:^|_)([a-z_]+)=([0-9a-z_]+?)(?=_[a-z_]+(?:=|$)|$)'
        matches = re.findall(pattern, name_without_ext)
        
        for key, value in matches:
            # Remove brackets if they exist (e.g., [12642] -> 12642)
            value = value.strip('[]')
            params[key] = value
        
        return params
    
    def get_file(self, taxon_id: str, folder_type: str, **kwargs) -> Optional[str]:
        """
        Get the path to a specific file based on search parameters.
        
        This method returns the first file matching all provided parameters.
        
        Args:
            taxon_id (str): Species identifier (e.g., '126421', '126426', '126822')
            folder_type (str): Type of folder: 'figures', 'metrics', 'models', or 'predictions'
            **kwargs: Variable parameters depending on folder_type:
                
                For 'figures':
                    method (str): e.g., 'maxent', 'rf', 'xgboost', 'ensemble'
                    what (str): e.g., 'responsecurves', 'shape'
                
                For 'metrics':
                    method (str): e.g., 'ensemble', 'maxent', 'rf', 'xgboost'
                    what (str): e.g., 'cvmetrics', 'fullmetrics', 'varimportance', 'biasmetrics'
                
                For 'models':
                    method (str): e.g., 'maxent', 'rf', 'xgboost'
                    what (str): Usually 'model'
                
                For 'predictions':
                    method (str): e.g., 'ensemble', 'maxent', 'rf', 'xgboost'
                    scen (str): e.g., '1990_2000', 'current', 'ssp585_dec100'
                    what (str): e.g., 'mess', 'shape'
        
        Returns:
            str or None: Full path to the file if found, None otherwise
        
        Example:
            # Get a specific predictions file for a time period
            path = manager.get_file(
                taxon_id='126421',
                folder_type='predictions',
                method='ensemble',
                scen='ssp585_dec100'
            )
            
            # Get metrics for a specific method
            path = manager.get_file(
                taxon_id='126421',
                folder_type='metrics',
                method='ensemble',
                what='cvmetrics'
            )
        """
        try:
            files = self.file_index[taxon_id][folder_type]
        except KeyError:
            return None
        
        # Search for the file matching all parameters
        for file_info in files:
            if self._matches_params(file_info['params'], kwargs):
                return file_info['path']
        
        return None
    
    def get_files(self, taxon_id: str, folder_type: str, **kwargs) -> List[str]:
        """
        Get all file paths matching the search parameters.
        
        This method returns all files that match the provided parameters. If no parameters
        are provided, it returns all files in the specified folder type.
        
        Args:
            taxon_id (str): Species identifier
            folder_type (str): Type of folder: 'figures', 'metrics', 'models', or 'predictions'
            **kwargs: Optional filtering parameters (see get_file for details)
        
        Returns:
            list: List of file paths matching the criteria. Empty list if no matches found.
        
        Example:
            # Get all predictions for a specific method
            files = manager.get_files(
                taxon_id='126421',
                folder_type='predictions',
                method='ensemble'
            )
            
            # Get all files for a scenario
            files = manager.get_files(
                taxon_id='126421',
                folder_type='predictions',
                scen='ssp585_dec100'
            )
            
            # Get all metric files
            files = manager.get_files(
                taxon_id='126421',
                folder_type='metrics'
            )
        """
        try:
            files = self.file_index[taxon_id][folder_type]
        except KeyError:
            return []
        
        matching_files = []
        for file_info in files:
            if self._matches_params(file_info['params'], kwargs):
                matching_files.append(file_info['path'])
        
        return matching_files
    
    def _matches_params(self, file_params: Dict, search_params: Dict) -> bool:
        """
        Check if file parameters match all search parameters.
        
        Args:
            file_params (dict): Parameters extracted from file name
            search_params (dict): Parameters to search for
        
        Returns:
            bool: True if all search parameters match, False otherwise
        """
        for key, value in search_params.items():
            if key not in file_params or file_params[key] != value:
                return False
        return True
    
    def get_file_info(self, taxon_id: str, folder_type: str, **kwargs) -> Optional[Dict]:
        """
        Get complete information about a file including path and extracted parameters.
        
        Args:
            taxon_id (str): Species identifier
            folder_type (str): Type of folder
            **kwargs: Search parameters
        
        Returns:
            dict or None: Dictionary with keys 'path', 'filename', 'extension', 'params'
                         or None if file not found
        """
        try:
            files = self.file_index[taxon_id][folder_type]
        except KeyError:
            return None
        
        for file_info in files:
            if self._matches_params(file_info['params'], kwargs):
                return file_info
        
        return None
    
    def list_taxons(self) -> List[str]:
        """
        Get a list of all available species (taxon IDs).
        
        Returns:
            list: Sorted list of taxon IDs (e.g., ['126421', '126426', '126822'])
        """
        return list(self.file_index.keys())
    
    def list_folder_types(self, taxon_id: str) -> List[str]:
        """
        Get a list of available folder types for a species.
        
        Args:
            taxon_id (str): Species identifier
        
        Returns:
            list: Available folder types (e.g., ['figures', 'metrics', 'models', 'predictions'])
        """
        return list(self.file_index.get(taxon_id, {}).keys())
    
    def list_parameters(self, taxon_id: str, folder_type: str) -> Dict[str, list]:
        """
        Get all unique parameter values available in a specific folder type.
        
        This method is useful for discovering what values are available for each parameter,
        helping you construct valid search queries.
        
        Args:
            taxon_id (str): Species identifier
            folder_type (str): Type of folder ('figures', 'metrics', 'models', 'predictions')
        
        Returns:
            dict: Dictionary where keys are parameter names and values are sorted lists
                  of available values for that parameter.
                  Example: {
                      'taxonid': ['126421'],
                      'model': ['mpaeu'],
                      'method': ['ensemble', 'maxent', 'rf', 'xgboost'],
                      'scen': ['1990_2000', '2000_2010', 'current', 'ssp585_dec100', ...],
                      'what': ['cvmetrics', 'fullmetrics', 'varimportance', ...]
                  }
        
        Example:
            params = manager.list_parameters('126421', 'predictions')
            print(params['scen'])  # ['1990_2000', '2000_2010', ..., 'ssp585_dec100']
        """
        params_dict = {}
        
        try:
            files = self.file_index[taxon_id][folder_type]
        except KeyError:
            return {}
        
        for file_info in files:
            for key, value in file_info['params'].items():
                if key not in params_dict:
                    params_dict[key] = set()
                params_dict[key].add(value)
        
        return {k: sorted(list(v)) for k, v in params_dict.items()}
    
    def print_usage_examples(self, taxon_id: Optional[str] = None):
        """
        Prints usage examples for the file manager.
        
        Args:
            taxon_id: ID of the species (if not provided, uses the first available)
        """
        if taxon_id is None:
            taxons = self.list_taxons()
            if not taxons:
                print("No specie available in the SDM root directory.")
                return
            taxon_id = taxons[0]
        
        print(f"\n{'='*60}")
        print(f"Usage examples for taxon_id={taxon_id}")
        print(f"{'='*60}\n")
        
        folder_types = self.list_folder_types(taxon_id)
        print(f"Available folder types: {folder_types}\n")
        
        for folder_type in folder_types:
            params = self.list_parameters(taxon_id, folder_type)
            if params:
                print(f"-- Folder '{folder_type}' --")
                print(f"Available parameters: {params}\n")
                
                # Generate search examples based on available parameters
                example_kwargs = {}
                
                # Priority of parameters to show
                priority_params = ['method', 'what', 'scen', 'scenario']
                
                for param in priority_params:
                    if param in params and params[param]:
                        example_kwargs[param] = params[param][0]
                        if len(example_kwargs) >= 2: 
                            break
                
                if example_kwargs:
                    print(f"Usage example:")
                    kwargs_str = ", ".join([f"{k}='{v}'" for k, v in example_kwargs.items()])
                    print(f"  manager.get_file(taxon_id='{taxon_id}', folder_type='{folder_type}',")
                    print(f"                   {kwargs_str})")
                else:
                    print(f"Usage example:")
                    print(f"  manager.get_files(taxon_id='{taxon_id}', folder_type='{folder_type}')")
                
                print()

# ----------------------------- EXAMPLE USAGE --------------------------------------:
sdm_root = r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results\SDMs"

# All methods properly documented with examples, parameter descriptions, and return types
manager = SDMFileManager(sdm_root)

# Select a taxon ID to use for all examples (change this to test different species)
taxon_id = '126426'

# Example 1: Get a specific prediction file
file_path = manager.get_file(
    taxon_id=taxon_id,
    folder_type='metrics',
    # method='ensemble',
    what='thresholds',
    # scen='2000_2010'    # To check all available scenarios, use example 3.
)
# print(f"File path: {file_path}; Exists: {os.path.exists(file_path) if file_path else False}")

# Example 2: Get all metrics for a method
files = manager.get_files(taxon_id=taxon_id, folder_type='metrics', method='ensemble')
# print(f"Metric files found: {files}")

# Example 3: List available scenarios
params = manager.list_parameters(taxon_id, 'predictions')
# print(f"Available scenarios: {params.get('scen', [])}")

# Example 4: List available methods
methods = manager.list_parameters(taxon_id, 'predictions')
# print(f"Available methods: {methods.get('method', [])}")






# -------------------------------------- FUNCTIONS TO COMPUTE CHAPTER RESULTS --------------------------------------:
# Function to compute presence/absence results
def compute_presence_absence(sdm_manager, presence_absence_dir,
                             taxon_ids: list[str] | str = None, 
                             methods: list[str] | str = None, 
                             scenarios: list[str] | str = None,
                             thresholds: list[str] | str = None) -> None:
    """
    Compute presence/absence results for combinations of taxon_id, method, and scenario.
    
    This function processes SDM prediction files and computes presence/absence data,
    saving results to the pre-created folder structure.
    
    Args:
        sdm_manager (SDMFileManager): SDM file manager instance
        presence_absence_dir (str): Output directory for presence/absence results
        taxon_ids (str or list): Taxon ID(s) to process. If None, processes all available.
                                Examples: '126421' or ['126421', '126426', '126822']
        methods (str or list): Methods to process. If None, processes all available.
                              Examples: 'ensemble' or ['ensemble', 'maxent', 'rf', 'xgboost']
        scenarios (str or list): Scenarios to process. If None, processes all available.
                                Examples: 'current' or ['current', 'ssp585_dec100', '2020_2024']
        thresholds (str or list): Threshold types to use for presence/absence calculation.
                                    If None, uses all available thresholds.
    
    Returns:
        None. Results are saved to disk in the presence_absence directory.
    
    Notes:
        - Requires that the output folder structure has been created (see create_presence_absence_structure)
        - Processes specified combinations iteratively
        - To be implemented: actual presence/absence calculation logic
    """
    
    # Convert single strings to lists for uniform processing
    if isinstance(taxon_ids, str):
        taxon_ids = [taxon_ids]
    elif taxon_ids is None:
        taxon_ids = sdm_manager.list_taxons()
    
    if isinstance(methods, str):
        methods = [methods]
    elif methods is None:
        methods = sdm_manager.list_parameters(taxon_ids[0], 'predictions').get('method', [])
    
    if isinstance(scenarios, str):
        scenarios = [scenarios]
    elif scenarios is None:
        scenarios = sdm_manager.list_parameters(taxon_ids[0], 'predictions').get('scen', [])
    
    if isinstance(thresholds, str):
        thresholds = [thresholds]
    elif thresholds is None:
        thresholds_df = None
        # Get all threshold options from the first taxon's thresholds file
        try:
            thresholds_file = sdm_manager.get_file(
                taxon_id=taxon_ids[0],
                folder_type='metrics',
                what='thresholds'
            )
            if thresholds_file:
                thresholds_df = pd.read_parquet(thresholds_file)
                # Filter thresholds from thresholds names:
                thresholds = [col for col in thresholds_df.columns if col != 'what']
            else:
                thresholds = []
        except:
            thresholds = []
    
    # Process each combination of taxon_id, method, scenario, and threshold
    for taxon_id in taxon_ids:
        for method in methods:
            for scenario in scenarios:
                for threshold in thresholds:
                    # Get prediction file
                    prediction_file = sdm_manager.get_file(
                        taxon_id=taxon_id,
                        folder_type='predictions',
                        method=method,
                        scen=scenario
                    )
                    
                    if prediction_file is None:
                        print(f"Warning: No prediction file found for taxon_id={taxon_id}, method={method}, scen={scenario}")
                        continue
                    
                    # Build output path
                    result_file = os.path.join(
                        presence_absence_dir,
                        f"taxonid={taxon_id}",
                        f"method={method}",
                        f"threshold={threshold}",
                        f"{scenario}.tif"
                    )

                    # Create output directory if it doesn't exist
                    Path(result_file).parent.mkdir(parents=True, exist_ok=True)

                    # Get thresholds DataFrame if not already loaded:
                    thresholds_file = sdm_manager.get_file(
                        taxon_id=taxon_id,
                        folder_type="metrics",
                        what="thresholds"
                    )

                    # Open thresholds file and read into DataFrame
                    thresholds_df = pd.read_parquet(thresholds_file)
                    print(thresholds_df)
                    # Filter threshold for current method:
                    print(method)
                    print(threshold)
                    threshold_value = thresholds_df.loc[thresholds_df["model"] == method, threshold].values[0]
                    print(threshold_value)
                    
                    # TODO: Implement actual presence/absence calculation
                    with rasterio.open(prediction_file) as prediction_src:
                        prediction = prediction_src.read(1) # read(2) for standard deviation id needed
                        nodata_value = prediction_src.nodata
                        
                        # Create presence/absence array with nodata preserved
                        presence_absence = np.where(prediction >= (threshold_value*100), 1, 0).astype(rasterio.uint8)
                        
                        # Preserve nodata values
                        if nodata_value is not None:
                            nodata_mask = prediction == nodata_value
                            presence_absence[nodata_mask] = nodata_value
                        
                        # Save presence/absence raster
                        profile = prediction_src.profile
                        profile.update(dtype=rasterio.uint8, count=1, nodata=nodata_value)
                        with rasterio.open(result_file, 'w', **profile) as dst:
                            dst.write(presence_absence, 1)
    
    print(f"\nPresence/Absence computation completed.")

# Function to create a table from presence/absence results table:
def create_presence_absence_table():
    """
    Generate a presence/absence table with spatial extent in hectares per stock area.
    Structure: Time frame | Stock 1 (ha) | Stock 2 (ha) | ...
    """
    
    TAXON_CONFIG = {
        126421: {
            'species_name': 'Sardina pilchardus',
            'stocks': [
                ('Divisions 8.c and 9.a', r'C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca\Stock_ICES_Areas\Sardina_pilchardus.shp'),
            ]
        },
        126426: {
            'species_name': 'Engraulis encrasicolus',
            'stocks': [
                ('Subarea 8', r'C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca\Stock_ICES_Areas\Engraulis_encrasicolus_subarea8.shp'),
                #('Division 9.a South', r'C:\path\to\shapefiles\engraulis_9a_south.shp'),
            ]
        },
        126822: {
            'species_name': 'Trachurus trachurus',
            'stocks': [
                ('Division 9.a', r'C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca\Stock_ICES_Areas\Trachurus_trachurus.shp'),
            ]
        },
    }
    
    BASE_PATH = r'C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results\presence_absence'
    
    # Temporal structure to store data
    temp_data = {
        'Time frame': [],
        'Species - Stock': [],
        'Extent (ha)': []
    }
    
    # Loop for each taxonid
    for taxonid, config in TAXON_CONFIG.items():
        species_name = config['species_name']
        
        taxon_path = os.path.join(BASE_PATH, f'taxonid={taxonid}', 'method=ensemble', 'threshold=max_spec_sens')    # Modify method & threshold as needed.
        
        if not os.path.exists(taxon_path):
            print(f"WARNING: Path not found for taxonid: {taxonid}")
            continue
        
        # Loop for each stock
        for stock_name, shapefile_path in config['stocks']:
            tif_files = {}
            for file in os.listdir(taxon_path):
                if file.endswith('.tif'):
                    if '2000_2010' in file:
                        tif_files['2000 - 2010'] = os.path.join(taxon_path, file)
                    elif '2010_2020' in file:
                        tif_files['2010 - 2020'] = os.path.join(taxon_path, file)
                    # Add scenarios as needed.
            
            # Compute extent for each period
        for period, tif_path in tif_files.items():
            if os.path.exists(tif_path):
                # Compute extent in hectares from SDM presence/absence in the stock area:
                extent_ha = calculate_extent_from_tif(tif_path, shapefile_path)
                
                # Temporal data:
                temp_data['Time frame'].append(period)
                temp_data['Species - Stock'].append(f'{species_name} {stock_name}')
                temp_data['Extent (ha)'].append(extent_ha)
    
    # Converto temporal to dataframe:
    df_temp = pd.DataFrame(temp_data)
    
    # Pivote table to desired format:
    df_pivot = df_temp.pivot_table(
        index='Time frame',
        columns='Species - Stock',
        values='Extent (ha)',
        aggfunc='first'
    )
    
    # Rename columns to include (ha)
    df_pivot.columns = [col + ' (ha)' for col in df_pivot.columns]
    
    # Create Net Change row
    net_change_row = df_pivot.loc['2010 - 2020'] - df_pivot.loc['2000 - 2010']
    net_change_row.name = 'Net Change'
    df_pivot = pd.concat([df_pivot, net_change_row.to_frame().T])
    
    # Reset index to have Tome frame in the first column:
    df_pivot.index.name = 'Time-frame'
    df_pivot = df_pivot.reset_index()
    df_pivot.columns.name = None
    
    return df_pivot

# Function to compute extent from presence/absence TIF using a mask:
def calculate_extent_from_tif(tif_path: str, shapefile_path: str) -> float:
    """
    Calculate extent in hectares from TIF file by vectorizing presence pixels.
    Vectorizes pixels with presence (=1), clips to the stock area shapefile and computes the geodesic area of the presence polygons.
    
    Args:
        tif_path : str. Path to the TIF file with presence/absence.
        shapefile_path : str. Path to the stock area shapefile

    Returns:
        float. Extension in hectares gcomputed as the geodesic area.
    """
    from rasterio.features import shapes
    import geopandas as gpd
    from shapely.geometry import shape

    # PROJ del venv (pyproj)
    os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()

    try:
        # Read shapefile of the stock area
        stock_gdf = gpd.read_file(shapefile_path)
        
        # Open the TIF and vectorize pixels with presence (value= 1)
        with rasterio.open(tif_path) as src:
            data = src.read(1)
            crs = src.crs
            
            # Vectorize: create polygons from pixels with value == 1
            presence_geometries = []
            for geom, value in shapes(data, transform=src.transform):
                if value == 1:  # Only pixels with presence
                    presence_geometries.append(shape(geom))
        
        # Create GeoDataFrame with presence geometries
        if not presence_geometries:
            print(f"No presence pixels found in {tif_path}")
            return 0.0
        
        gdf_presence = gpd.GeoDataFrame(geometry=presence_geometries, crs=crs)
        
        # Filter by stock area
        gdf_filtered = gpd.clip(gdf_presence, stock_gdf)
        
        if gdf_filtered.empty:
            print(f"No presence pixels found inside the stock assessment area in {tif_path}")
            return 0.0
        
        # Dissolve geometries
        gdf_dissolved = gdf_filtered.dissolve()
        
        # Calculate geodesic area directly in CRS 4326
        area_m2 = gdf_dissolved.geometry.to_crs('+proj=cea').area.sum()
        area_ha = area_m2 / 10000
        
        return area_ha
        
    except Exception as e:
        print(f"Error processing {tif_path}: {e}")
        import traceback
        traceback.print_exc()
        return 0.0
    

def graph_stocks(
    excel_file: str,
    sheet_name: Optional[str] = None,
    x: str = None,
    x_label: str = None,
    y: Union[str, Sequence[str]] = None,              
    y_label: Union[str, Sequence[str], None] = None,  
    color: Union[str, Sequence[str], None] = 'black',
    year_column: Optional[str] = None,
    year_range: Optional[tuple] = None,
    title: Optional[str] = None,
    figsize: tuple = (12, 6),
    show_plot: bool = True,
    save_path: Optional[str] = None
) -> None:
    """
    Generate plots from Excel file data with multiple sheets (one per stock).
    Allows plotting one or multiple Y series on the same axis.

    Args:
        excel_file: str. Path to the Excell file containing the data.
        sheet_name: str, optional. Name of the sheet to plot. If None, all sheets will be plotted.
        x: str. Column name for X-axis.
        x_label: str. Label for X-axis.
        y: str. Column name for Y-axis.
        y_label: str. Label for Y-axis.
        color: str, optional. Color for the plot line. Default is 'black'.
        year_column: str, optional. Column name containing year data. Used to filter by year_range.
        year_range: tuple, optional. Tuple (min_year, max_year) to filter data before plotting. Example: (2010, 2020) will only plot data from 2010 to 2020.
        title: str, optional. Title for the plot. If None, defaults to the sheet name.
        figsize: tuple. Figure size (width, height) in inches. Default: (12, 6).
        show_plot: bool. If True, display the plot. Default: True.
        save_path: str, optional. Path to save the plot. If None, plot is not saved.
    
    Returns:
        None. Displays and/or saves the plot.
    """

    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    # Validate inputs
    if x is None or y is None:
        raise ValueError("Both 'x' and 'y' column names must be provided.")

    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    # Normalize y to a list
    if isinstance(y, str):
        y_list = [y]
    else:
        y_list = list(y)

    # Determine series labels (legend labels)
    # - If y_label is a list -> use that as legend labels
    # - If y_label is a string -> use y column names as legend labels (and y_label for axis)
    # - If y_label is None -> use y column names
    axis_y_label = None
    if isinstance(y_label, (list, tuple)):
        series_labels = list(y_label)
        if len(series_labels) != len(y_list):
            raise ValueError("If 'y_label' is a list, it must have the same length as 'y'.")
        axis_y_label = "Value"  # o déjalo None si no quieres etiqueta por defecto
    else:
        series_labels = y_list[:]  # default legend labels = column names
        axis_y_label = y_label if isinstance(y_label, str) else None

    # Normalize colors
    if color is None:
        color_list = [None] * len(y_list)  # matplotlib elige
    elif isinstance(color, str):
        # si dan un único color y hay varias series, lo repetimos
        color_list = [color] * len(y_list)
    else:
        color_list = list(color)
        if len(color_list) != len(y_list):
            raise ValueError("If 'color' is a list, it must have the same length as 'y'.")

    # Determine which sheets to read
    if sheet_name:
        sheets = [sheet_name]
    else:
        sheets = pd.read_excel(excel_file, sheet_name=None).keys()

    # Process each sheet
    for sheet in sheets:
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet)

            # Validate columns exist
            if x not in df.columns:
                print(f"Warning: Column '{x}' not found in sheet '{sheet}'. Skipping.")
                continue

            missing_y = [col for col in y_list if col not in df.columns]
            if missing_y:
                print(f"Warning: Columns {missing_y} not found in sheet '{sheet}'. Skipping.")
                continue

            # Filter by year range if specified
            if year_range is not None and year_column is not None:
                if year_column not in df.columns:
                    print(f"Warning: Year column '{year_column}' not found in sheet '{sheet}'. No filtering applied.")
                else:
                    min_year, max_year = year_range
                    df = df[(df[year_column] >= min_year) & (df[year_column] <= max_year)]
                    if df.empty:
                        print(f"No data found for years {min_year}-{max_year} in sheet '{sheet}'.")
                        continue

            # Create plot
            fig, ax = plt.subplots(figsize=figsize)

            # Plot each Y series
            for yi, lbl, c in zip(y_list, series_labels, color_list):
                ax.plot(df[x], df[yi], marker='o', linewidth=2, markersize=6, label=lbl, color=c)

            # Format x-axis
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:.0f}'.format(v)))

            ax.set_xlabel(x_label if x_label else x, fontsize=12, fontweight='bold')

            # Y-axis label: only one axis label makes sense if multiple series
            if axis_y_label:
                ax.set_ylabel(axis_y_label, fontsize=12, fontweight='bold')
            else:
                # si solo hay una serie y no te pasaron y_label, usa el nombre de la columna
                if len(y_list) == 1:
                    ax.set_ylabel(y_list[0], fontsize=12, fontweight='bold')

            # Title
            if title:
                ax.set_title(title, fontsize=14, fontweight='bold')
            else:
                if len(y_list) == 1:
                    ax.set_title(f"{sheet} - {y_list[0]} vs {x}", fontsize=14, fontweight='bold')
                else:
                    ax.set_title(f"{sheet} - {', '.join(y_list)} vs {x}", fontsize=14, fontweight='bold')

            ax.grid(True, alpha=0.3)
            ax.legend()
            plt.tight_layout()

            # Save if requested
            if save_path:
                save_file = save_path.format(sheet=sheet) if "{sheet}" in save_path else save_path
                fig.savefig(save_file, dpi=300, bbox_inches='tight', format='png')
                print(f"Plot saved: {save_file}")

            if show_plot:
                plt.show()
            else:
                plt.close(fig)

        except Exception as e:
            print(f"Error processing sheet '{sheet}': {e}")