# app/models/model_b.py

import geopandas as gpd
from pyobis import occurrences
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps


def run():
    # Lógica de Model B
    return {"message": "Resultado de Model B"}

# shp = gpd.read_parquet(r"C:\Users\beñat.egidazu\Downloads\Fish.parquet")
# shp.to_file(r"C:\Users\beñat.egidazu\Downloads\Fish.shp")
