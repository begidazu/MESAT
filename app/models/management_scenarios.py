from typing import Any, List, Optional, Dict
import os
import pandas as pd                                                
import geopandas as gpd                                          
from shapely.geometry import Polygon, shape                      
from shapely.ops import unary_union, transform as shp_transform
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import reproject, Resampling

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
    "Santander": ["results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g.tif", "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g_accretion.tif"],
    "Cadiz_Bay": ["results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g.tif", "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif"],
    "Urdaibai_Estuary": ["results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g.tif", "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g_accretion.tif"]
}

SALTMARSH_SCENARIOS_PATHS = {
    "Santander": {
        "regional_rcp45": {
            "habitats": {
                "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2012_7g.tif",
                "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2062_7g.tif",
                "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2112_7g.tif"
            },
            "accretion": {
                "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2012_7g_accretion.tif",
                "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2062_7g_accretion.tif",
                "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2112_7g_accretion.tif"
            }
        },
        "regional_rcp85": {
            "habitats": {
                "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp45_2012_7g.tif",
                "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2062_7g.tif",
                "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2112_7g.tif"
            },
            "accretion": {
                "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp45_2012_7g_accretion.tif",
                "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2062_7g_accretion.tif",
                "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2112_7g_accretion.tif"
            }
        },
        "global_rcp45":  {
            "habitats": {
                "2012": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_reg_rcp45_2012_7g.tif",
                "2062": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2062_7g.tif",
                "2112": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2112_7g.tif"
            },
            "accretion": {
                "2012": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_reg_rcp45_2012_7g_accretion.tif",
                "2062": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2062_7g_accretion.tif",
                "2112": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2112_7g_accretion.tif"
            }
        }
    },

    "Cadiz_Bay": {
        "regional_rcp45": {
            "habitats": {
                "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2023_25g.tif",
                "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2073_25g.tif",
                "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2123_25g.tif"
            },
            "accretion": {
                "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2023_25g_accretion.tif",
                "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2073_25g_accretion.tif",
                "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2123_25g_accretion.tif"
            }
        },
        "regional_rcp85": {
            "habitats": {
                "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp45_2023_25g.tif",
                "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2073_25g.tif",
                "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2123_25g.tif"
            },
            "accretion": {
                "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp45_2023_25g_accretion.tif",
                "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2073_25g_accretion.tif",
                "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2123_25g_accretion.tif"
            }
        },
        "global_rcp45":  {
            "habitats": {
                "2023": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_reg_rcp45_2023_25g.tif",
                "2073": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2073_25g.tif",
                "2123": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2123_25g.tif"
            },
            "accretion": {
                "2023": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_reg_rcp45_2023_25g_accretion.tif",
                "2073": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2073_25g_accretion.tif",
                "2123": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2123_25g_accretion.tif"
            }
        }
    },

    "Urdaibai_Estuary": {
        "regional_rcp45": {
            "habitats": {
                "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2017_17g.tif",
                "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2067_17g.tif",
                "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2117_17g.tif"
            },
            "accretion": {
                "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2017_17g_accretion.tif",
                "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2067_17g_accretion.tif",
                "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2117_17g_accretion.tif"
            }
        },
        "regional_rcp85": {
            "habitats": {
                "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp45_2017_17g.tif",
                "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2067_17g.tif",
                "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2117_17g.tif"
            },
            "accretion": {
                "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp45_2017_17g_accretion.tif",
                "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2067_17g_accretion.tif",
                "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2117_17g_accretion.tif"
            }
        },
        "global_rcp45":  {
            "habitats": {
                "2017": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_reg_rcp45_2017_17g.tif",
                "2067": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2067_17g.tif",
                "2117": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2117_17g.tif"
            },
            "accretion": {
                "2017": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_reg_rcp45_2017_17g_accretion.tif",
                "2067": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2067_17g_accretion.tif",
                "2117": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2117_17g_accretion.tif"
            }
        }
    },
}

# Helpers for the paths:
def _norm(p): 
    return os.path.normpath(p) if p else None

def saltmarsh_scenario_available(area: str, scenario_key: str) -> bool:
    return bool(SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key))

def saltmarsh_scenario_years(area: str, scenario_key: str):
    node = SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key, {})
    years = list((node.get("habitats") or {}).keys())
    # orden numérico por si vienen como str
    try:
        years = sorted(years, key=lambda y: int(y))
    except Exception:
        years = sorted(years)
    return years

def saltmarsh_scenario_paths(area: str, scenario_key: str, year: str):
    node = SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key, {})
    h = _norm((node.get("habitats") or {}).get(year))
    a = _norm((node.get("accretion") or {}).get(year))
    return h, a

SALTMARSH_MAP: Dict[int, str] = {
    0: "Mudflat",
    1: "Saltmarsh",
    2: "Upland Areas",
    3: "Channel",
}

def saltmarsh_available(area: str) -> bool:
    return area in SALTMARSH_PATHS

def saltmarsh_habitat_path(area: str):
    paths = SALTMARSH_PATHS.get(area)
    return paths[0] if paths else None

def saltmarsh_accretion_path(area: str):
    paths = SALTMARSH_PATHS.get(area)
    return paths[1] if paths else None

# Function to merge both drawn and uploaded activities:
def _collect_activity_union(activity_children, activity_upload_children) -> gpd.GeoDataFrame:
    """Merge both drawn and uploaded polygons and returns a Geodataframe"""
    geoms = []
    if activity_children:
        for ch in (activity_children if isinstance(activity_children, list) else [activity_children]):
            if isinstance(ch, dict) and ch.get("type", "").endswith("Polygon"):
                pos = (ch.get("props", {}) or {}).get("positions") or []
                if pos and len(pos) >= 3:
                    ring = [(float(lon), float(lat)) for lat, lon in pos]  # [lat,lon] -> (lon,lat)
                    geoms.append(Polygon(ring))
    if activity_upload_children:
        for ch in (activity_upload_children if isinstance(activity_upload_children, list) else [activity_upload_children]):
            if isinstance(ch, dict) and ch.get("type", "").endswith("GeoJSON"):
                data = (ch.get("props", {}) or {}).get("data") or {}
                for f in data.get("features", []):
                    try:
                        geoms.append(shape(f.get("geometry")))
                    except Exception:
                        pass

    if not geoms:
        return gpd.GeoDataFrame(geometry=[], crs=4326)

    union = unary_union(geoms)
    if union.is_empty:
        return gpd.GeoDataFrame(geometry=[], crs=4326)

    geom = (unary_union([g for g in getattr(union, "geoms", [union])
                         if not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon")])
            if union.geom_type == "GeometryCollection" else union)

    gdf = gpd.GeoDataFrame(geometry=[geom], crs=4326)
    gdf["geometry"] = gdf.buffer(0)  # limpia posibles self-intersections
    return gdf

# Function to compute the EUNIS table:
def activity_eunis_table(area: str,
                     activity_children,
                     activity_upload_children,
                     label_col: str) -> pd.DataFrame:
    # 1) Unir geometrías user + upload
    geoms = []
    if activity_children:
        for ch in (activity_children if isinstance(activity_children, list) else [activity_children]):
            if isinstance(ch, dict) and ch.get("type","").endswith("Polygon"):
                pos = (ch.get("props",{}) or {}).get("positions") or []
                if pos and len(pos) >= 3:
                    ring = [(float(lon), float(lat)) for lat, lon in pos]  # [lat,lon] -> (lon,lat)
                    geoms.append(Polygon(ring))
    if activity_upload_children:
        for ch in (activity_upload_children if isinstance(activity_upload_children, list) else [activity_upload_children]):
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

# Function to compite pixel area in m2:
def _pixel_area_m2(transform) -> float:
    """Área de píxel en m² (válido para CRS proyectado)."""
    return abs(transform.a * transform.e - transform.b * transform.d)

# Function to compute saltmarsh affection:
def activity_saltmarsh_table(area: str,
                             activity_children,
                             activity_upload_children) -> pd.DataFrame:
    """
    Tabla por ecosistema (Mudflat, Saltmarsh, Upland Areas, Channel) con:
      - Extent (ha): área afectada dentro de los polígonos
      - Accretion (m³/yr): suma de acreción dentro de los políx. (solo Mudflat y Saltmarsh)
    Usa SALTMARSH_PATHS[area][0] (hábitat) y SALTMARSH_PATHS[area][1] (acreción).
    """
    ORDER = [0, 1, 2, 3]  # Mudflat, Saltmarsh, Upland Areas, Channel

    act = _collect_activity_union(activity_children, activity_upload_children)
    if act.empty:
        return pd.DataFrame({
            "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
            "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
            "Accretion (m³/yr)": [0.0, 0.0, "-", "-"],  # solo 0(Mudflat) y 1(Saltmarsh)
        })

    hab_path = saltmarsh_habitat_path(area)
    acc_path = saltmarsh_accretion_path(area)
    if not hab_path or not acc_path:
        raise ValueError(f"No hay TIFFs de saltmarsh para el área '{area}'.")

    with rasterio.open(hab_path) as hab_ds:
        if hab_ds.crs is None or hab_ds.crs.is_geographic:
            raise ValueError("El TIFF de hábitat debe tener un CRS proyectado (en metros).")

        # Geometría en CRS del ráster
        to_raster = Transformer.from_crs(act.crs, hab_ds.crs, always_xy=True).transform
        geom_in_raster = shp_transform(to_raster, act.geometry.iloc[0])

        # Clases recortadas (misma malla, sin crop)
        cls_arr, _ = rio_mask(hab_ds, [geom_in_raster], crop=False, filled=False)
        cls_ma = np.ma.masked_array(cls_arr[0], mask=np.ma.getmaskarray(cls_arr[0]))

        # Acreción en la malla del hábitat
        with rasterio.open(acc_path) as acc_ds:
            same_grid = (acc_ds.crs == hab_ds.crs and
                         acc_ds.transform == hab_ds.transform and
                         acc_ds.width == hab_ds.width and
                         acc_ds.height == hab_ds.height)

            if same_grid:
                acc_arr, _ = rio_mask(acc_ds, [geom_in_raster], crop=False, filled=False)
                acc_ma = np.ma.masked_array(acc_arr[0], mask=np.ma.getmaskarray(acc_arr[0]))
            else:
                acc_reproj = np.empty((hab_ds.height, hab_ds.width), dtype=np.float32)
                reproject(
                    source=rasterio.band(acc_ds, 1),
                    destination=acc_reproj,
                    src_transform=acc_ds.transform,
                    src_crs=acc_ds.crs,
                    dst_transform=hab_ds.transform,
                    dst_crs=hab_ds.crs,
                    resampling=Resampling.bilinear,
                )
                # máscara geométrica igual que clases
                acc_ma = np.ma.masked_array(acc_reproj, mask=cls_ma.mask)

        # Métrica por clase vía bincount (evita “corridos”)
        px_area_m2 = _pixel_area_m2(hab_ds.transform)
        px_area_ha = px_area_m2 / 10_000.0

        inside = ~cls_ma.mask
        classes = cls_ma.data[inside].astype(np.int64)

        # Extent: píxeles por clase * área de píxel
        counts = np.bincount(classes, minlength=4)
        extent_ha_by_code = counts * px_area_ha

        # Accretion: sum(espesor) por clase * área de píxel
        acc_filled = np.ma.filled(acc_ma, 0.0)
        acc_sums = np.bincount(classes,
                               weights=acc_filled[inside],
                               minlength=4) * px_area_m2

        # Construir filas en el orden deseado
        rows = []
        for code in ORDER:
            name = SALTMARSH_MAP[code]
            extent_ha = round(float(extent_ha_by_code[code]), 2)
            if code in (0, 1):  # Mudflat y Saltmarsh
                acc_val = round(float(acc_sums[code]), 2)
            else:
                acc_val = "-"
            rows.append((name, extent_ha, acc_val))

    return pd.DataFrame(rows, columns=["Ecosystem", "Extent (ha)", "Accretion (m³/yr)"])

# Function to compute activity affection to saltmarsh and mudflats in the x scenario and y year:
def activity_saltmarsh_scenario_table(area: str,
                                      scenario_key: str,
                                      year: str,
                                      activity_children,
                                      activity_upload_children) -> pd.DataFrame:
    ORDER = [0, 1, 2, 3]  # Mudflat, Saltmarsh, Upland Areas, Channel

    # Unión de polígonos
    act = _collect_activity_union(activity_children, activity_upload_children)
    if act.empty:
        return pd.DataFrame({
            "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
            "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
            "Accretion (m³/yr)": [0.0, 0.0, "-", "-"],
        })

    # Rutas por escenario/año
    hab_path, acc_path = saltmarsh_scenario_paths(area, scenario_key, year)
    if not (hab_path and acc_path):
        # sin rutas → devolver tabla vacía “suave”
        return pd.DataFrame({
            "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
            "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
            "Accretion (m³/yr)": ["-", "-", "-", "-"],
        })

    with rasterio.open(hab_path) as hab_ds:
        if hab_ds.crs is None or hab_ds.crs.is_geographic:
            raise ValueError("Habitat TIFF must be in a projected CRS (meters).")

        to_raster = Transformer.from_crs(act.crs, hab_ds.crs, always_xy=True).transform
        geom_in_raster = shp_transform(to_raster, act.geometry.iloc[0])

        cls_arr, _ = rio_mask(hab_ds, [geom_in_raster], crop=False, filled=False)
        cls_ma = np.ma.masked_array(cls_arr[0], mask=np.ma.getmaskarray(cls_arr[0]))

        with rasterio.open(acc_path) as acc_ds:
            same_grid = (acc_ds.crs == hab_ds.crs and
                         acc_ds.transform == hab_ds.transform and
                         acc_ds.width == hab_ds.width and
                         acc_ds.height == hab_ds.height)
            if same_grid:
                acc_arr, _ = rio_mask(acc_ds, [geom_in_raster], crop=False, filled=False)
                acc_ma = np.ma.masked_array(acc_arr[0], mask=np.ma.getmaskarray(acc_arr[0]))
            else:
                acc_reproj = np.empty((hab_ds.height, hab_ds.width), dtype=np.float32)
                reproject(
                    source=rasterio.band(acc_ds, 1),
                    destination=acc_reproj,
                    src_transform=acc_ds.transform,
                    src_crs=acc_ds.crs,
                    dst_transform=hab_ds.transform,
                    dst_crs=hab_ds.crs,
                    resampling=Resampling.bilinear,
                )
                acc_ma = np.ma.masked_array(acc_reproj, mask=cls_ma.mask)

        px_area_m2 = _pixel_area_m2(hab_ds.transform)
        px_area_ha = px_area_m2 / 10_000.0

        inside = ~cls_ma.mask
        classes = cls_ma.data[inside].astype(np.int64)

        counts = np.bincount(classes, minlength=4)
        extent_ha_by_code = counts * px_area_ha

        acc_filled = np.ma.filled(acc_ma, 0.0)
        acc_sums_m3yr = np.bincount(classes,
                                    weights=acc_filled[inside],
                                    minlength=4) * px_area_m2

        rows = []
        for code in ORDER:
            name = SALTMARSH_MAP[code]
            extent_ha = round(float(extent_ha_by_code[code]), 2)
            if code in (0, 1):
                acc_val = round(float(acc_sums_m3yr[code]), 2)
            else:
                acc_val = "-"
            rows.append((name, extent_ha, acc_val))

    return pd.DataFrame(rows, columns=["Ecosystem", "Extent (ha)", "Accretion (m³/yr)"])