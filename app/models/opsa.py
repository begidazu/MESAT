# app/models/model_a.py

import os
import geopandas as gpd

file_path = r"C:\Users\beñat.egidazu\Desktop\PhD\Papers\Physical_Accounts\Souther_Gulf_Biscay\EUNIS\EUNIS_BBT_Southern_Gulf_Biscay_clean.shp"
def to_geoparquet(in_path: str, out_path: str):

    gdf = gpd.read_file(file_path)
    # asegúrate de tener CRS
    if gdf.crs is None:
        raise ValueError(f"Sin CRS en {in_path}")
    gdf.to_parquet(out_path, compression="zstd")  # o "snappy"

# ejemplo:
base = "results/OPSA/Santander"

to_geoparquet(file_path, os.path.join(base, "eunis_santander.parquet"))
print("Shapefile converted to GeoParquet!")

