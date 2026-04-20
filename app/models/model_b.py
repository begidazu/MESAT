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