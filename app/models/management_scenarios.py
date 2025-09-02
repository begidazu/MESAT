from typing import Any, List, Optional
import pandas as pd                                                
import geopandas as gpd                                          
from shapely.geometry import Polygon, shape                      
from shapely.ops import unary_union                           

EUNIS_PATHS = {
    "Santander":  "results/opsa/Santander/eunis_santander.parquet",     
    "North_Sea":  "results/opsa/North_Sea/eunis_north_sea.parquet",    
    "Irish_Sea":  "results/opsa/Irish_Sea/eunis_irish_sea.parquet",     
}

def eunis_available(area: str) -> bool:                
    return area in EUNIS_PATHS                               

def eunis_path(area: str):                                 
    return EUNIS_PATHS.get(area) 

SALTMARSH_PATHS = {
    "Santander": ["results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g.tif", "results/saltmarshes/regional_rcp45/santander_reg_rcp45_2012_7g_accretion.tif"],
    "Cadiz_Bay": ["results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g.tif", "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif"],
    "Urdaibai_Estuary": ["results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g.tif", "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g_accretion.tif"]
}

def saltmarsh_available(area: str) -> bool:
    return area in SALTMARSH_PATHS

def saltmarsh_habitat_path(area: str):
    paths = SALTMARSH_PATHS.get(area)
    return paths[0] if paths else None

def saltmarsh_accretion_path(area: str):
    paths = SALTMARSH_PATHS.get(area)
    return paths[1] if paths else None