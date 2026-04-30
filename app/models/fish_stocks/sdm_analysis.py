import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Sequence, Union, Tuple
import pyproj
import rasterio
from rasterio.mask import mask
import numpy as np
import pandas as pd
import geopandas as gpd

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
                 'ssp585_dec50', 'ssp585_dec100', '2000_2010_high', '2000_2010_low', '2010_2020_high', '2010_2020_low')
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
        # Captures values with underscores, letters, and hyphens (e.g., 1990_2000, 2000_2010_high)
        # Stops before:
        # - The next parameter (which has format _key=value)
        # - A suffix (e.g., _cog, _mess, _shape)
        # - End of string
        pattern = r'(?:^|_)([a-z_]+)=([0-9a-z_-]+?)(?=_[a-z_]+=[0-9a-z_-]|_[a-z]+$|$)'
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
# sdm_root = r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results\SDMs"

# # All methods properly documented with examples, parameter descriptions, and return types
# manager = SDMFileManager(sdm_root)

# # Select a taxon ID to use for all examples (change this to test different species)
# taxon_id = '126426'

# # Example 1: Get a specific prediction file
# file_path = manager.get_file(
#     taxon_id=taxon_id,
#     folder_type='metrics',
#     # method='ensemble',
#     what='thresholds',
#     # scen='2000_2010'    # To check all available scenarios, use example 3.
# )
# # print(f"File path: {file_path}; Exists: {os.path.exists(file_path) if file_path else False}")

# # Example 2: Get all metrics for a method
# files = manager.get_files(taxon_id=taxon_id, folder_type='metrics', method='ensemble')
# # print(f"Metric files found: {files}")

# # Example 3: List available scenarios
# params = manager.list_parameters(taxon_id, 'predictions')
# # print(f"Available scenarios: {params.get('scen', [])}")

# # Example 4: List available methods
# methods = manager.list_parameters(taxon_id, 'predictions')
# # print(f"Available methods: {methods.get('method', [])}")






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
        # 126421: {
        #     'species_name': 'Sardina pilchardus',
        #     'stocks': [
        #         ('Sardina pilchardus in Cantabrian Sea and Atlantic Iberian waters', r'"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca\Stock_ICES_Areas\pil_27_8c9a.shp"'),
        #     ]
        # },
        126426: {
            'species_name': 'Engraulis encrasicolus',
            'stocks': [
                #('Engraulis encrasicolus in Bay of Biscay', r'"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca\Stock_ICES_Areas\ane_27_8.shp"'),
                ('Engraulis encrasicolus in Division 9.a South', r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\ane_27_9aS.shp"),
            ]
        },
        # 126822: {
        #     'species_name': 'Trachurus trachurus',
        #     'stocks': [
        #         ('Trachurus trachurusin Atlantic Iberian waters', r'C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\hom_27_9a.shp'),
        #         ('Trachurus trachurus in Northeast Atlantic and adjacent waters', r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\hom_27_2a3a4a5b6a7a__ce_k8.shp")
        #     ]
        # },
        # 127023: {
        #     'species_name': 'Scomber scombrus',
        #     'stocks': [
        #         ('Scomber scombrus in Northeast Atlantic and adjacent waters', r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\mac_27_nea.shp")
        #     ]
        # }
    }
    
    BASE_PATH = r'C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct\presence_absence'
    
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
                    if '2000_2010_high' in file:
                        tif_files['2000 - 2010 High'] = os.path.join(taxon_path, file)
                    elif '2000_2010_low' in file:
                        tif_files['2000 - 2010 Low'] = os.path.join(taxon_path, file)
                    elif '2000_2010' in file and '2000_2010_high' not in file and '2000_2010_low' not in file:
                        tif_files['2000 - 2010'] = os.path.join(taxon_path, file)
                    elif '2010_2020_high' in file:
                        tif_files['2010 - 2020 High'] = os.path.join(taxon_path, file)
                    elif '2010_2020_low' in file:
                        tif_files['2010 - 2020 Low'] = os.path.join(taxon_path, file)
                    elif '2010_2020' in file and '2010_2020_high' not in file and '2010_2020_low' not in file:
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
    
    # Create Net Change rows for each scenario (High, Low, or base)
    # Check which scenarios exist and calculate changes accordingly
    rows_to_add = []
    
    # Calculate change for High scenarios
    if '2010 - 2020 High' in df_pivot.index and '2000 - 2010 High' in df_pivot.index:
        net_change_high = df_pivot.loc['2010 - 2020 High'] - df_pivot.loc['2000 - 2010 High']
        net_change_high.name = 'Net Change High'
        rows_to_add.append(net_change_high)
    
    # Calculate change for Low scenarios
    if '2010 - 2020 Low' in df_pivot.index and '2000 - 2010 Low' in df_pivot.index:
        net_change_low = df_pivot.loc['2010 - 2020 Low'] - df_pivot.loc['2000 - 2010 Low']
        net_change_low.name = 'Net Change Low'
        rows_to_add.append(net_change_low)
    
    # Calculate change for base scenarios (without High/Low)
    if '2010 - 2020' in df_pivot.index and '2000 - 2010' in df_pivot.index:
        net_change_base = df_pivot.loc['2010 - 2020'] - df_pivot.loc['2000 - 2010']
        net_change_base.name = 'Net Change'
        rows_to_add.append(net_change_base)
    
    # Add all calculated rows
    if rows_to_add:
        df_pivot = pd.concat([df_pivot] + [row.to_frame().T for row in rows_to_add])
    
    # Reset index to have Time frame in the first column:
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
    color: Union[str, Sequence[str], None] = None,
    color_sheet: Union[str, Sequence[str], None] = None,
    color_y: Union[str, Sequence[str], None] = None,
    year_column: Optional[str] = None,
    year_range: Optional[tuple] = None,
    title: Optional[str] = None,
    figsize: tuple = (12, 6),
    show_plot: bool = True,
    save_path: Optional[str] = None,
    combine_sheets: bool = False,
    use_subplots: bool = False,
    y_names_dict: Optional[Dict[str, str]] = None,
    sheet_labels: Optional[Union[Dict[str, str], Sequence[str]]] = None,
    show_legend: bool = True
) -> None:
    """
    Generate plots from Excel file data with multiple sheets (one per stock).
    Allows plotting one or multiple Y series on the same axis.

    Args:
        excel_file: str. Path to the Excell file containing the data.
        sheet_name: str or list, optional. 
            - If str: Name of the sheet to plot.
            - If list: List of sheet names to plot.
            - If None: All sheets will be plotted.
        x: str. Column name for X-axis.
        x_label: str. Label for X-axis.
        y: str. Column name for Y-axis.
        y_label: str. Label for Y-axis.
        color: str or list, optional. DEPRECATED: Use color_sheet or color_y instead.
        color_sheet: str or list, optional. Color(s) for each sheet. 
            - If str: Single color (repeated for all sheets)
            - If list: List of colors. Length must match number of sheets when combine_sheets=True.
            Default is None (auto-select colors).
        color_y: str or list, optional. Color(s) for each Y indicator. 
            - If str: Single color (repeated for all series)
            - If list: List of colors. Length must match number of Y columns.
            Default is None (auto-select colors).
        year_column: str, optional. Column name containing year data. Used to filter by year_range.
        year_range: tuple, optional. Tuple (min_year, max_year) to filter data before plotting. Example: (2010, 2020) will only plot data from 2010 to 2020.
        title: str, optional. Title for the plot. If None, defaults based on context.
        figsize: tuple. Figure size (width, height) in inches. Default: (12, 6).
        show_plot: bool. If True, display the plot. Default: True.
        save_path: str, optional. Path to save the plot. If None, plot is not saved.
        combine_sheets: bool. If True, all sheets are plotted on the same graph with different colors.
                        If False (default), each sheet gets its own plot.
        use_subplots: bool. If True and combine_sheets=True, creates multiple subplots (one per stock)
                      instead of a single combined plot. Default: False.
        y_names_dict: dict, optional. Dictionary mapping Y column names to custom legend labels.
                      Example: {'ReproductiveCapacityNormalized': 'RC', 'RecruitmentNormalized': 'RN'}.
                      If a Y column is not in the dictionary, the column name is used as label.
                      Default: None.
        sheet_labels: dict or list, optional. Custom labels for each subplot (top-left corner).
                      - If dict: Maps sheet names to custom labels. Example: {'sheet1': 'Label A', 'sheet2': 'Label B'}.
                      - If list: Labels in the same order as sheet_name. Example: ['Label A', 'Label B'].
                      - If None: Uses sheet names as labels (default behavior).
                      Default: None.
        show_legend: bool. If True, display the legend. If False, no legend is shown. Default: True.
    
    Returns:
        None. Displays and/or saves the plot(s).
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

    # Normalize y_names_dict
    if y_names_dict is None:
        y_names_dict = {}
    # Function to get label for a Y column (use custom name if available, else use column name)
    def get_y_label(col_name):
        return y_names_dict.get(col_name, col_name)

    # Determine series labels (legend labels) for individual Y series
    # - If y_label is a list -> use that as legend labels
    # - If y_label is a string -> use y column names as legend labels (and y_label for axis)
    # - If y_label is None -> use y column names
    axis_y_label = None
    if isinstance(y_label, (list, tuple)):
        series_labels = list(y_label)
        if len(series_labels) != len(y_list):
            raise ValueError("If 'y_label' is a list, it must have the same length as 'y'.")
        axis_y_label = "Value"
    else:
        series_labels = y_list[:]  # default legend labels = column names
        axis_y_label = y_label if isinstance(y_label, str) else None

    # Determine which sheets to read
    if sheet_name:
        if isinstance(sheet_name, str):
            sheets = [sheet_name]
        else:
            sheets = list(sheet_name)  # convert list/tuple to list
    else:
        sheets = list(pd.read_excel(excel_file, sheet_name=None).keys())

    # Handle deprecated 'color' parameter
    if color is not None:
        if color_y is None and color_sheet is None:
            # If only 'color' is provided, use it as color_y (for backward compatibility with subplots)
            color_y = color
        elif color_y is None:
            color_y = color
    
    # Normalize colors for sheets
    if color_sheet is None:
        color_sheet_list = [None] * len(sheets)
    elif isinstance(color_sheet, str):
        color_sheet_list = [color_sheet] * len(sheets)
    else:
        color_sheet_list = list(color_sheet)
        if len(color_sheet_list) != len(sheets):
            raise ValueError("If 'color_sheet' is a list, it must have the same length as the number of sheets.")
    
    # Normalize colors for Y indicators
    if color_y is None:
        color_y_list = [None] * len(y_list)
    elif isinstance(color_y, str):
        color_y_list = [color_y] * len(y_list)
    else:
        color_y_list = list(color_y)
        if len(color_y_list) != len(y_list):
            raise ValueError("If 'color_y' is a list, it must have the same length as 'y'.")

    # Normalize sheet_labels
    sheet_labels_dict = {}
    if sheet_labels is not None:
        if isinstance(sheet_labels, dict):
            sheet_labels_dict = sheet_labels
        elif isinstance(sheet_labels, (list, tuple)):
            sheet_labels_list = list(sheet_labels)
            if len(sheet_labels_list) != len(sheets):
                raise ValueError("If 'sheet_labels' is a list, it must have the same length as the number of sheets.")
            sheet_labels_dict = {sheet: label for sheet, label in zip(sheets, sheet_labels_list)}
    
    # Function to get label for a sheet (use custom label if available, else use sheet name)
    def get_sheet_label(sheet_name_val):
        return sheet_labels_dict.get(sheet_name_val, sheet_name_val)

    # ============ COMBINED MODE (multiple stocks in one plot or subplots) ============
    if combine_sheets:
        try:
            import math
            
            # Collect data for all sheets first
            data_dict = {}
            valid_sheets = []
            
            for sheet_idx, sheet in enumerate(sheets):
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet)

                    # Validate columns exist
                    if x not in df.columns:
                        print(f"Warning: Column '{x}' not found in sheet '{sheet}'. Skipping.")
                        continue

                    # Check which Y columns exist in this sheet (don't skip if some are missing)
                    available_y = [col for col in y_list if col in df.columns]
                    if not available_y:
                        print(f"Warning: None of the columns {y_list} found in sheet '{sheet}'. Skipping.")
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

                    # Store all available Y data for this sheet
                    data_dict[sheet] = {'x': df[x], 'y_data': {y_col: df[y_col] for y_col in available_y}, 'color': color_sheet_list[sheet_idx], 'available_y': available_y}
                    valid_sheets.append(sheet)

                except Exception as e:
                    print(f"Error processing sheet '{sheet}': {e}")

            if not valid_sheets:
                print("No valid sheets found to plot.")
                return

            # ========== SUBPLOT MODE ==========
            if use_subplots:
                num_stocks = len(valid_sheets)
                cols = int(math.ceil(math.sqrt(num_stocks)))
                rows = int(math.ceil(num_stocks / cols))
                
                fig, axes = plt.subplots(rows, cols, figsize=figsize, sharex=True, sharey=True)
                
                # Flatten axes array if it's 2D
                if num_stocks > 1:
                    axes = axes.flatten()
                else:
                    axes = [axes]
                
                for ax_idx, sheet in enumerate(valid_sheets):
                    ax = axes[ax_idx]
                    sheet_data = data_dict[sheet]
                    x_data = sheet_data['x']
                    y_data_dict = sheet_data['y_data']
                    available_y = sheet_data['available_y']
                    sheet_color = sheet_data['color']
                    
                    # Plot all available Y columns for this sheet with different colors
                    for y_idx, y_col in enumerate(available_y):
                        y_label_custom = get_y_label(y_col)
                        # Use sheet color if provided, otherwise use color for this Y indicator
                        if sheet_color is not None:
                            c = sheet_color
                        else:
                            orig_y_idx = y_list.index(y_col)
                            c = color_y_list[orig_y_idx]
                        ax.plot(x_data, y_data_dict[y_col], linewidth=2, label=y_label_custom, color=c)
                    
                    # Get the label for this sheet (custom label if provided, else sheet name)
                    sheet_label = get_sheet_label(sheet)
                    # Add label in top-left corner
                    ax.text(0.02, 0.98, sheet_label, transform=ax.transAxes, 
                            fontsize=11, fontweight='bold', verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                    
                    ax.set_xlabel(x_label if x_label else x, fontsize=10)
                    ax.set_ylabel(axis_y_label if axis_y_label else "Indicator scores", fontsize=10)
                    ax.grid(True, alpha=0.3)
                    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:.0f}'.format(v)))
                    if show_legend:
                        ax.legend(fontsize=9)
                
                # Hide unused subplots
                for ax_idx in range(num_stocks, len(axes)):
                    axes[ax_idx].set_visible(False)
                
                # Add overall title
                if title:
                    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.00)
                else:
                    fig.suptitle(f"Condition Indicators across stocks", fontsize=14, fontweight='bold', y=1.00)
                
                plt.tight_layout()

                # Save if requested
                if save_path:
                    fig.savefig(save_path, dpi=300, bbox_inches='tight', format='png')
                    print(f"Plot saved: {save_path}")

                if show_plot:
                    plt.show()
                else:
                    plt.close(fig)

            # ========== SINGLE PLOT MODE ==========
            else:
                fig, ax = plt.subplots(figsize=figsize)

                for sheet in valid_sheets:
                    x_data, y_data, c = data_dict[sheet]
                    ax.plot(x_data, y_data, linewidth=2, label=sheet, color=c)

                # Format x-axis
                ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:.0f}'.format(v)))

                ax.set_xlabel(x_label if x_label else x, fontsize=12, fontweight='bold')
                ax.set_ylabel(axis_y_label if axis_y_label else y_list[0], fontsize=12, fontweight='bold')

                # Title
                if title:
                    ax.set_title(title, fontsize=14, fontweight='bold')
                else:
                    ax.set_title(f"Comparison of {y_list[0]} across stocks", fontsize=14, fontweight='bold')

                ax.grid(True, alpha=0.3)
                if show_legend:
                    ax.legend()
                plt.tight_layout()

                # Save if requested
                if save_path:
                    fig.savefig(save_path, dpi=300, bbox_inches='tight', format='png')
                    print(f"Plot saved: {save_path}")

                if show_plot:
                    plt.show()
                else:
                    plt.close(fig)

        except Exception as e:
            print(f"Error creating combined plot: {e}")

    # ============ SEPARATE MODE (one plot per sheet) ============
    else:
        # Process each sheet
        for sheet in sheets:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet)

                # Validate columns exist
                if x not in df.columns:
                    print(f"Warning: Column '{x}' not found in sheet '{sheet}'. Skipping.")
                    continue

                # Check which Y columns exist in this sheet (don't skip if some are missing)
                available_y = [col for col in y_list if col in df.columns]
                if not available_y:
                    print(f"Warning: None of the columns {y_list} found in sheet '{sheet}'. Skipping.")
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

                # Plot each available Y series with custom labels
                for y_idx, y_col in enumerate(available_y):
                    y_label_custom = get_y_label(y_col)
                    # Map to the corresponding color in color_y_list based on position in original y_list
                    orig_y_idx = y_list.index(y_col)
                    c = color_y_list[orig_y_idx]
                    ax.plot(df[x], df[y_col], linewidth=2, label=y_label_custom, color=c)

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
                if show_legend:
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


# Function to compute Abiotic State condtion index from suitability maps:
def create_stock_index_table_from_suitability(
    sdm_manager,
    presence_absence_base: str,
    taxon_config: Dict,
    timeframes: Dict[str, str],
    method: str = "ensemble",
    threshold: str = "max_spec_sens",
    print_esref: bool = True,
) -> pd.DataFrame:
    """
    Generate a stock-level suitability index table using ensemble SDM predictions.

    The resulting DataFrame has:
        - Rows: Time frames
        - Columns: "Species - Stock"
        - Values: Index = avg(ES) / (avg(ES) + ESref)

    Definitions
    ----------
    avg(ES) for timeframe t and stock S:
        Mean suitability score (ensemble model) inside the stock polygon,
        considering ONLY cells where presence/absence == 1 for that timeframe.

    ESref for stock S:
        Median suitability score (ensemble model) computed by pooling ALL
        timeframes together, but in each timeframe including ONLY cells where
        presence == 1 within that stock.

    The suitability rasters are forced to be the files ending in "_cog.tif":
        taxonid=<id>_model=mpaeu_method=ensemble_scen=<timeframe>_cog.tif

    The index is computed as:
        Index = avg(ES) / (avg(ES) + ESref)

    Since both avg(ES) and ESref are on the same scale (0–100),
    no normalization is required.

    Parameters
    ----------
    sdm_manager : SDMFileManager
        Instance of your SDMFileManager class.
        Used to retrieve ensemble prediction rasters from the 'predictions' folder.

    presence_absence_base : str
        Base directory where presence/absence rasters are stored.
        Expected structure:
            presence_absence_base/
                taxonid=<id>/
                    method=<method>/
                        threshold=<threshold>/
                            <timeframe>.tif

    taxon_config : dict
        Dictionary defining species and their stock shapefiles.
        Structure must follow:

        {
            taxonid: {
                "species_name": "Species scientific name",
                "stocks": [
                    (stock_name, shapefile_path),
                    ...
                ]
            },
            ...
        }

    timeframes : dict
        Dictionary mapping scenario keys to display labels.
        Example:
            {
                "2000_2010": "2000 - 2010",
                "2010_2020": "2010 - 2020"
            }

        Keys must match the "scen=" argument used in prediction filenames.

    method : str, optional (default="ensemble")
        SDM method to use. In your case, predictions are taken from:
            method=ensemble

    threshold : str, optional (default="max_spec_sens")
        Name of the threshold folder used for presence/absence rasters.
        Must match:
            threshold=<threshold>

    print_esref : bool, optional (default=True)
        If True, prints for each stock:
            - ESref median value
            - Number of cells used
        Useful for debugging and validating reference values.

    Returns
    -------
    pd.DataFrame
        Pivoted DataFrame with:
            - First column: "Time-frame"
            - Other columns: "<Species> <Stock> (Index)"
            - Values: avg(ES)/(avg(ES) + ESref)

        If no valid data is found, returns an empty DataFrame with column "Time-frame".
    """

    def _read_masked_array(tif_path: str, polygon_gdf: gpd.GeoDataFrame):
        """Read raster and mask it to the stock polygon."""
        with rasterio.open(tif_path) as src:
            g = polygon_gdf.to_crs(src.crs)
            out, _ = mask(src, g.geometry, crop=True, filled=False)
            return out[0], src.nodata

    rows = []
    esref_pool: Dict[Tuple[int, str], List[float]] = {}

    # ------------------------------------------------------------------
    # 1) Compute ESref (median pooling all timeframes)
    # ------------------------------------------------------------------

    for taxonid, cfg in taxon_config.items():
        for stock_name, shp_path in cfg["stocks"]:
            stock_gdf = gpd.read_file(shp_path)
            key = (taxonid, stock_name)
            esref_pool[key] = []

            for tf_key in timeframes.keys():

                pa_path = os.path.join(
                    presence_absence_base,
                    f"taxonid={taxonid}",
                    f"method={method}",
                    f"threshold={threshold}",
                    f"{tf_key}.tif",
                )
                if not os.path.exists(pa_path):
                    continue

                candidates = sdm_manager.get_files(
                    taxon_id=str(taxonid),
                    folder_type="predictions",
                    method=method,
                    scen=tf_key,
                )
                candidates = [f for f in candidates if f.endswith("_cog.tif")]

                if len(candidates) == 0:
                    continue
                if len(candidates) > 1:
                    raise ValueError(
                        f"Multiple suitability '_cog.tif' files found for "
                        f"taxonid={taxonid}, scen={tf_key}: {candidates}"
                    )

                es_path = candidates[0]

                pa_arr, pa_nodata = _read_masked_array(pa_path, stock_gdf)
                es_arr, es_nodata = _read_masked_array(es_path, stock_gdf)

                if pa_arr.shape != es_arr.shape:
                    raise ValueError(
                        f"Grid mismatch for taxonid={taxonid}, "
                        f"stock='{stock_name}', timeframe='{tf_key}'."
                    )

                valid_mask = (pa_arr == 1)
                if pa_nodata is not None:
                    valid_mask &= (pa_arr != pa_nodata)
                if es_nodata is not None:
                    valid_mask &= (es_arr != es_nodata)

                vals = es_arr[valid_mask]
                if vals.size > 0:
                    esref_pool[key].extend(vals.astype("float32").tolist())

    esref_median: Dict[Tuple[int, str], float] = {}
    for key, vals in esref_pool.items():
        esref_median[key] = float(np.median(vals)) if len(vals) else np.nan

        if print_esref:
            taxonid, stock_name = key
            print(
                f"[ESref] taxonid={taxonid} | stock='{stock_name}' "
                f"| median={esref_median[key]} | n={len(vals)}"
            )

    # ------------------------------------------------------------------
    # 2) Compute median(ES) per timeframe and build index
    # ------------------------------------------------------------------

    for taxonid, cfg in taxon_config.items():
        species_name = cfg["species_name"]

        for stock_name, shp_path in cfg["stocks"]:
            stock_gdf = gpd.read_file(shp_path)
            key = (taxonid, stock_name)
            esref = esref_median.get(key, np.nan)

            for tf_key, tf_label in timeframes.items():

                pa_path = os.path.join(
                    presence_absence_base,
                    f"taxonid={taxonid}",
                    f"method={method}",
                    f"threshold={threshold}",
                    f"{tf_key}.tif",
                )
                if not os.path.exists(pa_path):
                    continue

                candidates = sdm_manager.get_files(
                    taxon_id=str(taxonid),
                    folder_type="predictions",
                    method=method,
                    scen=tf_key,
                )
                candidates = [f for f in candidates if f.endswith("_cog.tif")]

                if len(candidates) == 0:
                    continue
                if len(candidates) > 1:
                    raise ValueError(
                        f"Multiple suitability '_cog.tif' files found for "
                        f"taxonid={taxonid}, scen={tf_key}: {candidates}"
                    )

                es_path = candidates[0]

                pa_arr, pa_nodata = _read_masked_array(pa_path, stock_gdf)
                es_arr, es_nodata = _read_masked_array(es_path, stock_gdf)

                if pa_arr.shape != es_arr.shape:
                    raise ValueError(
                        f"Grid mismatch for taxonid={taxonid}, "
                        f"stock='{stock_name}', timeframe='{tf_key}'."
                    )

                valid_mask = (pa_arr == 1)
                if pa_nodata is not None:
                    valid_mask &= (pa_arr != pa_nodata)
                if es_nodata is not None:
                    valid_mask &= (es_arr != es_nodata)

                vals = es_arr[valid_mask]

                if vals.size == 0 or not np.isfinite(esref):
                    idx_value = np.nan
                else:
                    median_es = float(np.median(vals.astype("float32")))
                    denom = median_es + float(esref)
                    idx_value = (median_es / denom) if denom != 0 else np.nan

                rows.append(
                    {
                        "Time frame": tf_label,
                        "Species - Stock": f"{species_name} {stock_name}",
                        "Index": idx_value,
                    }
                )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["Time-frame"])

    df_pivot = df.pivot_table(
        index="Time frame",
        columns="Species - Stock",
        values="Index",
        aggfunc="first",
    )

    df_pivot.columns = [col + " (Index)" for col in df_pivot.columns]
    df_pivot.index.name = "Time-frame"
    df_pivot = df_pivot.reset_index()
    df_pivot.columns.name = None

    return df_pivot