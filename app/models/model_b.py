# app/models/model_b.py

import geopandas as gpd
import pandas as pd
from pyobis import occurrences
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps


def run():
    # Lógica de Model B
    return {"message": "Resultado de Model B"}

# # shp = gpd.read_parquet(r"C:\Users\beñat.egidazu\Downloads\Fish.parquet")
# # shp.to_file(r"C:\Users\beñat.egidazu\Downloads\Fish.shp")

# table = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\mac_27_nea.shp")
# table.to_parquet(r"C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\macnea.parquet")

# import rasterio

# files = {
#     'ANE8': r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\presence_absence\taxonid=126426\method=ensemble\threshold=max_spec_sens\2000_2010.tif',
#     'MACNEA': r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\presence_absence\taxonid=127023\method=ensemble\threshold=max_spec_sens\2000_2010.tif',
#     'HOMNEA': r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\presence_absence\taxonid=126822\method=ensemble\threshold=max_spec_sens\2000_2010_0_25deg.tif',
#     # add others
# }

# for name, path in files.items():
#     with rasterio.open(path) as src:
#         print(f"{name}: CRS={src.crs}, bounds={src.bounds}, shape={src.shape}, dtype={src.dtypes}")