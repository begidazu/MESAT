# app/models/model_a.py

import os
import geopandas as gpd

def run():
    """
    Lógica de Model A: lee sample_data.geojson en data/
    y devuelve un resumen sencillo.
    """
    # 1) Construye la ruta al directorio data/
    base_dir = os.path.dirname(__file__)                          # .../app/models
    repo_root = os.path.abspath(os.path.join(base_dir, os.pardir, os.pardir))
    data_dir = os.path.join(repo_root, "data")
    sample_path = os.path.join(data_dir, "sample_data.geojson")

    # 2) Comprueba que el fichero existe
    if not os.path.exists(sample_path):
        # Podrías lanzar FileNotFoundError o devolver un dict de error
        return {"error": f"No existe {sample_path}"}

    # 3) Carga con GeoPandas
    df = gpd.read_file(sample_path)

    # 4) Devuelve un resumen, por ejemplo el número de geometrías
    return {"n_geoms": len(df)}
