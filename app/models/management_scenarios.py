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

# Function to compute the EUNIS table:
def wind_eunis_table(area: str,
                     wind_children,
                     wind_upload_children,
                     label_col: str) -> pd.DataFrame:
    # 1) Unir geometrías user + upload
    geoms = []
    if wind_children:
        for ch in (wind_children if isinstance(wind_children, list) else [wind_children]):
            if isinstance(ch, dict) and ch.get("type","").endswith("Polygon"):
                pos = (ch.get("props",{}) or {}).get("positions") or []
                if pos and len(pos) >= 3:
                    ring = [(float(lon), float(lat)) for lat, lon in pos]  # [lat,lon] -> (lon,lat)
                    geoms.append(Polygon(ring))
    if wind_upload_children:
        for ch in (wind_upload_children if isinstance(wind_upload_children, list) else [wind_upload_children]):
            if isinstance(ch, dict) and ch.get("type","").endswith("GeoJSON"):
                data = (ch.get("props",{}) or {}).get("data") or {}
                for f in data.get("features", []):
                    try:
                        geoms.append(shape(f.get("geometry")))
                    except Exception:
                        pass

    if not geoms:
        return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])

    union = unary_union(geoms)
    act = gpd.GeoDataFrame(geometry=[union] if union.geom_type!="GeometryCollection" else list(union), crs=4326)
    act["geometry"] = act.buffer(0)  # limpia posibles self-intersections

    # 2) Cargar EUNIS
    p = eunis_path(area)
    if not p:
        return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])
    eunis = gpd.read_parquet(p) if p.lower().endswith(".parquet") else gpd.read_file(p)
    eunis = eunis.to_crs(4326) if eunis.crs else eunis.set_crs(4326)
    eunis["geometry"] = eunis.buffer(0)

    # 3) Usar la columna pasada por el usuario
    if not label_col:
        raise ValueError("Debes pasar 'label_col' con el nombre de la columna de hábitat.")
    cols_map = {c.lower(): c for c in eunis.columns}
    label_key = cols_map.get(label_col.lower())  # solo normalizo mayúsculas/minúsculas
    if not label_key:
        raise KeyError(f"Columna '{label_col}' no existe en EUNIS. Columnas disponibles: {list(eunis.columns)}")

    cond_col = "condition" if "condition" in eunis.columns else ("Condition" if "Condition" in eunis.columns else None)
    keep_cols = [label_key, "geometry"] + ([cond_col] if cond_col else [])
    eunis_sub = eunis[keep_cols].copy()

    # 4) Intersección y áreas
    try:
        inter = gpd.overlay(eunis_sub, act[["geometry"]], how="intersection")
    except Exception:
        inter = gpd.overlay(eunis_sub.buffer(0), act.buffer(0)[["geometry"]], how="intersection")

    if inter.empty:
        return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])

    inter_m = inter.to_crs(3035)
    inter["area_km2"] = inter_m.area / 1e6

    # 5) Agregado por hábitat
    if cond_col:
        inter = inter.rename(columns={cond_col: "cond"})
        out = (inter.groupby(label_key)
                    .apply(lambda g: pd.Series({
                        "Extent (km²)": g["area_km2"].sum(),
                        "Condition": (g["cond"] * g["area_km2"]).sum() / g["area_km2"].sum()
                    }))
                    .reset_index()
                    .rename(columns={label_key: "EUNIS habitat"}))
    else:
        out = (inter.groupby(label_key, as_index=False)["area_km2"].sum()
                    .rename(columns={label_key:"EUNIS habitat","area_km2":"Extent (km²)"}))
        out["Condition"] = pd.NA

    out["Extent (km²)"] = out["Extent (km²)"].round(3)
    if "Condition" in out.columns:
        out["Condition"] = out["Condition"].round(2)
    return out