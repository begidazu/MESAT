# app/models/model_b.py
import pandas as pd
import geopandas as gpd
from pyobis import occurrences
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps


def run():
    # Lógica de Model B
    return {"message": "Resultado de Model B"}

# # Leer el shapefile
# study_area = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\Ines_Study_Area\Geopark_Oeste\Geopark_Oeste_Final.shp")

# # Guardar como Parquet (usando pyarrow)
# study_area.to_parquet(
#     r"C:\Users\beñat.egidazu\Desktop\Tests\Ines_Study_Area\Geopark_Oeste\Geopark_Oeste_Final.parquet",
#     engine="pyarrow"
# )