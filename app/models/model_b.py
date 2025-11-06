# app/models/model_b.py

import geopandas as gpd
from pyobis import occurrences
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps


def run():
    # Lógica de Model B
    return {"message": "Resultado de Model B"}

# shp = gpd.read_file(r"D:\Papers\Saltmarshes\Modelos\IH\Santander\data\random_500_points.shp")
# shp.to_parquet(r"D:\Papers\Saltmarshes\Modelos\IH\Santander\data\santander_bay_training_dataset.parquet")
