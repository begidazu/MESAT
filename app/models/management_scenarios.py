# VERSION 23/03/2026 FUNCIONANDO

# from typing import Any, List, Optional, Dict
# import os
# import pandas as pd                                                
# import geopandas as gpd                                          
# from shapely.geometry import Polygon, shape                      
# from shapely.ops import unary_union, transform as shp_transform
# import numpy as np
# from pyproj import Transformer
# import rasterio
# from rasterio.mask import mask as rio_mask
# from rasterio.warp import reproject, Resampling

# EUNIS_PATHS = {
#     "Santander":  "results/opsa/Santander/eunis_santander.parquet",     
#     "North_Sea":  "results/opsa/North_Sea/eunis_north_sea.parquet",    
#     "Irish_Sea":  "results/opsa/Irish_Sea/eunis_irish_sea.parquet",     
# }

# def eunis_available(area: str) -> bool:                
#     return area in EUNIS_PATHS                               


# def eunis_path(area: str):
#     return EUNIS_PATHS.get(area)

# # def eunis_path(area: str):
# #     """Devuelve la ruta absoluta al parquet EUNIS del área.
# #     CAMBIO: Convierte ruta relativa a absoluta para uso en producción."""
# #     rel_path = EUNIS_PATHS.get(area)
# #     return resolve_path(rel_path) if rel_path else None 

# SALTMARSH_PATHS = {
#     "Santander": ["results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g.tif", "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g_accretion.tif"],
#     "Cadiz_Bay": ["results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g.tif", "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif"],
#     "Urdaibai_Estuary": ["results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g.tif", "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g_accretion.tif"]
# }

# SALTMARSH_SCENARIOS_PATHS = {
#     "Santander": {
#         "regional_rcp45": {
#             "habitats": {
#                 "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g.tif",
#                 "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2062_7g.tif",
#                 "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2112_7g.tif"
#                 # "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2012_7g.tif",
#                 # "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2062_7g.tif",
#                 # "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2112_7g.tif"
#             },
#             "accretion": {
#                 "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g_accretion.tif",
#                 "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2062_7g_accretion.tif",
#                 "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2112_7g_accretion.tif"
#                 # "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2012_7g_accretion.tif",
#                 # "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2062_7g_accretion.tif",
#                 # "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp45\santander_reg_rcp45_2112_7g_accretion.tif"
#             }
#         },
#         "regional_rcp85": {
#             "habitats": {
#                 "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp45_2012_7g.tif",
#                 "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2062_7g.tif",
#                 "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2112_7g.tif"
#                 # "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp45_2012_7g.tif",
#                 # "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2062_7g.tif",
#                 # "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2112_7g.tif" 
#             },
#             "accretion": {
#                 "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp45_2012_7g_accretion.tif",
#                 "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2062_7g_accretion.tif",
#                 "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2112_7g_accretion.tif"
#                 # "2012": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp45_2012_7g_accretion.tif",
#                 # "2062": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2062_7g_accretion.tif",
#                 # "2112": r"results\saltmarshes\Bay_of_Santander\regional_rcp85\santander_reg_rcp85_2112_7g_accretion.tif"
#             }
#         },
#         "global_rcp45":  {
#             "habitats": {
#                 "2012": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_reg_rcp45_2012_7g.tif",
#                 "2062": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2062_7g.tif",
#                 "2112": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2112_7g.tif"
#                 # "2012": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_reg_rcp45_2012_7g.tif",
#                 # "2062": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2062_7g.tif",
#                 # "2112": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2112_7g.tif"
#             },
#             "accretion": {
#                 "2012": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_reg_rcp45_2012_7g_accretion.tif",
#                 "2062": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2062_7g_accretion.tif",
#                 "2112": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2112_7g_accretion.tif"
#                 # "2012": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_reg_rcp45_2012_7g_accretion.tif",
#                 # "2062": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2062_7g_accretion.tif",
#                 # "2112": r"results\saltmarshes\Bay_of_Santander\global_rcp45\santander_glo_rcp45_2112_7g_accretion.tif"
#             }
#         }
#     },

#     "Cadiz_Bay": {
#         "regional_rcp45": {
#             "habitats": {
#                 "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g.tif",
#                 "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2073_25g.tif",
#                 "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2123_25g.tif"
#                 # "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2023_25g.tif",
#                 # "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2073_25g.tif",
#                 # "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2123_25g.tif"
#             },
#             "accretion": {
#                 "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif",
#                 "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2073_25g_accretion.tif",
#                 "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2123_25g_accretion.tif"
#                 # "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2023_25g_accretion.tif",
#                 # "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2073_25g_accretion.tif",
#                 # "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp45\cadiz_reg_rcp45_2123_25g_accretion.tif"
#             }
#         },
#         "regional_rcp85": {
#             "habitats": {
#                 "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp45_2023_25g.tif",
#                 "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2073_25g.tif",
#                 "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2123_25g.tif"
#                 # "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp45_2023_25g.tif",
#                 # "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2073_25g.tif",
#                 # "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2123_25g.tif"
#             },
#             "accretion": {
#                 "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp45_2023_25g_accretion.tif",
#                 "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2073_25g_accretion.tif",
#                 "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2123_25g_accretion.tif"
#                 # "2023": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp45_2023_25g_accretion.tif",
#                 # "2073": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2073_25g_accretion.tif",
#                 # "2123": r"results\saltmarshes\Cadiz_Bay\regional_rcp85\cadiz_reg_rcp85_2123_25g_accretion.tif"
#             }
#         },
#         "global_rcp45":  {
#             "habitats": {
#                 "2023": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_reg_rcp45_2023_25g.tif",
#                 "2073": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2073_25g.tif",
#                 "2123": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2123_25g.tif"
#                 # "2023": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_reg_rcp45_2023_25g.tif",
#                 # "2073": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2073_25g.tif",
#                 # "2123": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2123_25g.tif"
#             },
#             "accretion": {
#                 "2023": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif",
#                 "2073": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2073_25g_accretion.tif",
#                 "2123": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2123_25g_accretion.tif"
#                 # "2023": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_reg_rcp45_2023_25g_accretion.tif",
#                 # "2073": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2073_25g_accretion.tif",
#                 # "2123": r"results\saltmarshes\Cadiz_Bay\global_rcp45\cadiz_glo_rcp45_2123_25g_accretion.tif"
#             }
#         }
#     },

#     "Urdaibai_Estuary": {
#         "regional_rcp45": {
#             "habitats": {
#                 "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g.tif",
#                 "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2067_17g.tif",
#                 "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2117_17g.tif"
#                 # "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2017_17g.tif",
#                 # "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2067_17g.tif",
#                 # "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2117_17g.tif"
#             },
#             "accretion": {
#                 "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g_accretion.tif",
#                 "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2067_17g_accretion.tif",
#                 "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2117_17g_accretion.tif"
#                 # "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2017_17g_accretion.tif",
#                 # "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2067_17g_accretion.tif",
#                 # "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp45\oka_reg_rcp45_2117_17g_accretion.tif"
#             }
#         },
#         "regional_rcp85": {
#             "habitats": {
#                 "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp45_2017_17g.tif",
#                 "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2067_17g.tif",
#                 "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2117_17g.tif"
#                 # "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp45_2017_17g.tif",
#                 # "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2067_17g.tif",
#                 # "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2117_17g.tif"
#             },
#             "accretion": {
#                 "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp45_2017_17g_accretion.tif",
#                 "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2067_17g_accretion.tif",
#                 "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2117_17g_accretion.tif"
#                 # "2017": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp45_2017_17g_accretion.tif",
#                 # "2067": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2067_17g_accretion.tif",
#                 # "2117": r"results\saltmarshes\Urdaibai_Estuary\regional_rcp85\oka_reg_rcp85_2117_17g_accretion.tif"
#             }
#         },
#         "global_rcp45":  {
#             "habitats": {
#                 "2017": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_reg_rcp45_2017_17g.tif",
#                 "2067": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2067_17g.tif",
#                 "2117": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2117_17g.tif"
#                 # "2017": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_reg_rcp45_2017_17g.tif",
#                 # "2067": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2067_17g.tif",
#                 # "2117": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2117_17g.tif"
#             },
#             "accretion": {
#                 "2017": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_reg_rcp45_2017_17g_accretion.tif",
#                 "2067": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2067_17g_accretion.tif",
#                 "2117": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2117_17g_accretion.tif"
#                 # "2017": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_reg_rcp45_2017_17g_accretion.tif",
#                 # "2067": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2067_17g_accretion.tif",
#                 # "2117": r"results\saltmarshes\Urdaibai_Estuary\global_rcp45\oka_glo_rcp45_2117_17g_accretion.tif"
#             }
#         }
#     },
# }

# # Helpers for the paths:
# def _norm(p): 
#     return os.path.normpath(p) if p else None

# def saltmarsh_scenario_available(area: str, scenario_key: str) -> bool:
#     return bool(SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key))

# def saltmarsh_scenario_years(area: str, scenario_key: str):
#     node = SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key, {})
#     years = list((node.get("habitats") or {}).keys())
#     # orden numérico por si vienen como str
#     try:
#         years = sorted(years, key=lambda y: int(y))
#     except Exception:
#         years = sorted(years)
#     return years

# def saltmarsh_scenario_paths(area: str, scenario_key: str, year: str):
#     """Devuelve las rutas de habitat y accretion para un escenario y año.
#     CAMBIO: Convierte rutas relativas a absolutas para uso en producción."""
#     node = SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key, {})
#     h = _norm((node.get("habitats") or {}).get(year))
#     a = _norm((node.get("accretion") or {}).get(year))
#     # h_rel = (node.get("habitats") or {}).get(year)
#     # a_rel = (node.get("accretion") or {}).get(year)
#     # h = resolve_path(h_rel) if h_rel else None
#     # a = resolve_path(a_rel) if a_rel else None
#     return h, a

# SALTMARSH_MAP: Dict[int, str] = {
#     0: "Mudflat",
#     1: "Saltmarsh",
#     2: "Upland Areas",
#     3: "Channel",
# }

# def saltmarsh_available(area: str) -> bool:
#     return area in SALTMARSH_PATHS

# # BACKUP ORIGINAL: 
# def saltmarsh_habitat_path(area: str):
#     paths = SALTMARSH_PATHS.get(area)
#     return paths[0] if paths else None

# # def saltmarsh_habitat_path(area: str):
# #     """Devuelve la ruta absoluta del TIF de habitat de saltmarsh del área.
# #     CAMBIO: Convierte ruta relativa a absoluta para uso en producción."""
# #     paths = SALTMARSH_PATHS.get(area)
# #     if paths:
# #         return resolve_path(paths[0])
# #     return None

# # BACKUP ORIGINAL: 
# def saltmarsh_accretion_path(area: str): 
#     paths = SALTMARSH_PATHS.get(area)
#     return paths[1] if paths else None

# # def saltmarsh_accretion_path(area: str):
# #     """Devuelve la ruta absoluta del TIF de accretion de saltmarsh del área.
# #     CAMBIO: Convierte ruta relativa a absoluta para uso en producción."""
# #     paths = SALTMARSH_PATHS.get(area)
# #     if paths:
# #         return resolve_path(paths[1])
# #     return None

# # Function to merge both drawn and uploaded activities:
# def _collect_activity_union(activity_children, activity_upload_children) -> gpd.GeoDataFrame:
#     """Merge both drawn and uploaded polygons and returns a Geodataframe"""
#     geoms = []
#     if activity_children:
#         for ch in (activity_children if isinstance(activity_children, list) else [activity_children]):
#             if isinstance(ch, dict) and ch.get("type", "").endswith("Polygon"):
#                 pos = (ch.get("props", {}) or {}).get("positions") or []
#                 if pos and len(pos) >= 3:
#                     ring = [(float(lon), float(lat)) for lat, lon in pos]  # [lat,lon] -> (lon,lat)
#                     geoms.append(Polygon(ring))
#     if activity_upload_children:
#         for ch in (activity_upload_children if isinstance(activity_upload_children, list) else [activity_upload_children]):
#             if isinstance(ch, dict) and ch.get("type", "").endswith("GeoJSON"):
#                 data = (ch.get("props", {}) or {}).get("data") or {}
#                 for f in data.get("features", []):
#                     try:
#                         geoms.append(shape(f.get("geometry")))
#                     except Exception:
#                         pass

#     if not geoms:
#         return gpd.GeoDataFrame(geometry=[], crs=4326)

#     union = unary_union(geoms)
#     if union.is_empty:
#         return gpd.GeoDataFrame(geometry=[], crs=4326)

#     geom = (unary_union([g for g in getattr(union, "geoms", [union])
#                          if not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon")])
#             if union.geom_type == "GeometryCollection" else union)

#     gdf = gpd.GeoDataFrame(geometry=[geom], crs=4326)
#     gdf["geometry"] = gdf.buffer(0)  # limpia posibles self-intersections
#     return gdf

# # Function to compute the EUNIS table:
# def activity_eunis_table(area: str,
#                      activity_children,
#                      activity_upload_children,
#                      label_col: str) -> pd.DataFrame:
#     # 1) Unir geometrías user + upload
#     geoms = []
#     if activity_children:
#         for ch in (activity_children if isinstance(activity_children, list) else [activity_children]):
#             if isinstance(ch, dict) and ch.get("type","").endswith("Polygon"):
#                 pos = (ch.get("props",{}) or {}).get("positions") or []
#                 if pos and len(pos) >= 3:
#                     ring = [(float(lon), float(lat)) for lat, lon in pos]  # [lat,lon] -> (lon,lat)
#                     geoms.append(Polygon(ring))
#     if activity_upload_children:
#         for ch in (activity_upload_children if isinstance(activity_upload_children, list) else [activity_upload_children]):
#             if isinstance(ch, dict) and ch.get("type","").endswith("GeoJSON"):
#                 data = (ch.get("props",{}) or {}).get("data") or {}
#                 for f in data.get("features", []):
#                     try:
#                         geoms.append(shape(f.get("geometry")))
#                     except Exception:
#                         pass

#     if not geoms:
#         return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])

#     union = unary_union(geoms)
#     act = gpd.GeoDataFrame(geometry=[union] if union.geom_type!="GeometryCollection" else list(union), crs=4326)
#     act["geometry"] = act.buffer(0)  # limpia posibles self-intersections

#     # 2) Cargar EUNIS
#     p = eunis_path(area)
#     if not p:
#         return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])
#     eunis = gpd.read_parquet(p) if p.lower().endswith(".parquet") else gpd.read_file(p)
#     eunis = eunis.to_crs(4326) if eunis.crs else eunis.set_crs(4326)
#     eunis["geometry"] = eunis.buffer(0)

#     # 3) Usar la columna pasada por el usuario
#     if not label_col:
#         raise ValueError("Debes pasar 'label_col' con el nombre de la columna de hábitat.")
#     cols_map = {c.lower(): c for c in eunis.columns}
#     label_key = cols_map.get(label_col.lower())  # solo normalizo mayúsculas/minúsculas
#     if not label_key:
#         raise KeyError(f"Columna '{label_col}' no existe en EUNIS. Columnas disponibles: {list(eunis.columns)}")

#     cond_col = "condition" if "condition" in eunis.columns else ("Condition" if "Condition" in eunis.columns else None)
#     keep_cols = [label_key, "geometry"] + ([cond_col] if cond_col else [])
#     eunis_sub = eunis[keep_cols].copy()

#     # 4) Intersección y áreas
#     try:
#         inter = gpd.overlay(eunis_sub, act[["geometry"]], how="intersection")
#     except Exception:
#         inter = gpd.overlay(eunis_sub.buffer(0), act.buffer(0)[["geometry"]], how="intersection")

#     if inter.empty:
#         return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])

#     inter_m = inter.to_crs(3035)
#     inter["area_km2"] = inter_m.area / 1e6

#     # 5) Agregado por hábitat
#     if cond_col:
#         inter = inter.rename(columns={cond_col: "cond"})
#         out = (inter.groupby(label_key)
#                     .apply(lambda g: pd.Series({
#                         "Extent (km²)": g["area_km2"].sum(),
#                         "Condition": (g["cond"] * g["area_km2"]).sum() / g["area_km2"].sum()
#                     }))
#                     .reset_index()
#                     .rename(columns={label_key: "EUNIS habitat"}))
#     else:
#         out = (inter.groupby(label_key, as_index=False)["area_km2"].sum()
#                     .rename(columns={label_key:"EUNIS habitat","area_km2":"Extent (km²)"}))
#         out["Condition"] = pd.NA

#     out["Extent (km²)"] = out["Extent (km²)"].round(3)
#     if "Condition" in out.columns:
#         out["Condition"] = out["Condition"].round(2)
#     return out

# # Function to compite pixel area in m2:
# def _pixel_area_m2(transform) -> float:
#     """Área de píxel en m² (válido para CRS proyectado)."""
#     return abs(transform.a * transform.e - transform.b * transform.d)

# # Function to compute saltmarsh affection:
# def activity_saltmarsh_table(area: str,
#                              activity_children,
#                              activity_upload_children) -> pd.DataFrame:
#     """
#     Tabla por ecosistema (Mudflat, Saltmarsh, Upland Areas, Channel) con:
#       - Extent (ha): área afectada dentro de los polígonos
#       - Accretion (m³/yr): suma de acreción dentro de los políx. (solo Mudflat y Saltmarsh)
#     Usa SALTMARSH_PATHS[area][0] (hábitat) y SALTMARSH_PATHS[area][1] (acreción).
#     """
#     ORDER = [0, 1, 2, 3]  # Mudflat, Saltmarsh, Upland Areas, Channel

#     act = _collect_activity_union(activity_children, activity_upload_children)
#     if act.empty:
#         return pd.DataFrame({
#             "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
#             "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
#             "Accretion (m³/yr)": [0.0, 0.0, "-", "-"],  # solo 0(Mudflat) y 1(Saltmarsh)
#         })

#     hab_path = saltmarsh_habitat_path(area)
#     acc_path = saltmarsh_accretion_path(area)
#     if not hab_path or not acc_path:
#         raise ValueError(f"No hay TIFFs de saltmarsh para el área '{area}'.")

#     with rasterio.open(hab_path) as hab_ds:
#         if hab_ds.crs is None or hab_ds.crs.is_geographic:
#             raise ValueError("El TIFF de hábitat debe tener un CRS proyectado (en metros).")

#         # Geometría en CRS del ráster
#         to_raster = Transformer.from_crs(act.crs, hab_ds.crs, always_xy=True).transform
#         geom_in_raster = shp_transform(to_raster, act.geometry.iloc[0])

#         # Clases recortadas (misma malla, sin crop)
#         cls_arr, _ = rio_mask(hab_ds, [geom_in_raster], crop=False, filled=False)
#         cls_ma = np.ma.masked_array(cls_arr[0], mask=np.ma.getmaskarray(cls_arr[0]))

#         # Acreción en la malla del hábitat
#         with rasterio.open(acc_path) as acc_ds:
#             same_grid = (acc_ds.crs == hab_ds.crs and
#                          acc_ds.transform == hab_ds.transform and
#                          acc_ds.width == hab_ds.width and
#                          acc_ds.height == hab_ds.height)

#             if same_grid:
#                 acc_arr, _ = rio_mask(acc_ds, [geom_in_raster], crop=False, filled=False)
#                 acc_ma = np.ma.masked_array(acc_arr[0], mask=np.ma.getmaskarray(acc_arr[0]))
#             else:
#                 acc_reproj = np.empty((hab_ds.height, hab_ds.width), dtype=np.float32)
#                 reproject(
#                     source=rasterio.band(acc_ds, 1),
#                     destination=acc_reproj,
#                     src_transform=acc_ds.transform,
#                     src_crs=acc_ds.crs,
#                     dst_transform=hab_ds.transform,
#                     dst_crs=hab_ds.crs,
#                     resampling=Resampling.bilinear,
#                 )
#                 # máscara geométrica igual que clases
#                 acc_ma = np.ma.masked_array(acc_reproj, mask=cls_ma.mask)

#         # Métrica por clase vía bincount (evita “corridos”)
#         px_area_m2 = _pixel_area_m2(hab_ds.transform)
#         px_area_ha = px_area_m2 / 10_000.0

#         inside = ~cls_ma.mask
#         classes = cls_ma.data[inside].astype(np.int64)

#         # Extent: píxeles por clase * área de píxel
#         counts = np.bincount(classes, minlength=4)
#         extent_ha_by_code = counts * px_area_ha

#         # Accretion: sum(espesor) por clase * área de píxel
#         acc_filled = np.ma.filled(acc_ma, 0.0)
#         acc_sums = np.bincount(classes,
#                                weights=acc_filled[inside],
#                                minlength=4) * px_area_m2

#         # Construir filas en el orden deseado
#         rows = []
#         for code in ORDER:
#             name = SALTMARSH_MAP[code]
#             extent_ha = round(float(extent_ha_by_code[code]), 2)
#             if code in (0, 1):  # Mudflat y Saltmarsh
#                 acc_val = round(float(acc_sums[code]), 2)
#             else:
#                 acc_val = "-"
#             rows.append((name, extent_ha, acc_val))

#     return pd.DataFrame(rows, columns=["Ecosystem", "Extent (ha)", "Accretion (m³/yr)"])

# # Function to compute activity affection to saltmarsh and mudflats in the x scenario and y year:
# def activity_saltmarsh_scenario_table(area: str,
#                                       scenario_key: str,
#                                       year: str,
#                                       activity_children,
#                                       activity_upload_children) -> pd.DataFrame:
#     ORDER = [0, 1, 2, 3]  # Mudflat, Saltmarsh, Upland Areas, Channel

#     # Unión de polígonos
#     act = _collect_activity_union(activity_children, activity_upload_children)
#     if act.empty:
#         return pd.DataFrame({
#             "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
#             "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
#             "Accretion (m³/yr)": [0.0, 0.0, "-", "-"],
#         })

#     # Rutas por escenario/año
#     hab_path, acc_path = saltmarsh_scenario_paths(area, scenario_key, year)
#     if not (hab_path and acc_path):
#         # sin rutas → devolver tabla vacía “suave”
#         return pd.DataFrame({
#             "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
#             "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
#             "Accretion (m³/yr)": ["-", "-", "-", "-"],
#         })

#     with rasterio.open(hab_path) as hab_ds:
#         if hab_ds.crs is None or hab_ds.crs.is_geographic:
#             raise ValueError("Habitat TIFF must be in a projected CRS (meters).")

#         to_raster = Transformer.from_crs(act.crs, hab_ds.crs, always_xy=True).transform
#         geom_in_raster = shp_transform(to_raster, act.geometry.iloc[0])

#         cls_arr, _ = rio_mask(hab_ds, [geom_in_raster], crop=False, filled=False)
#         cls_ma = np.ma.masked_array(cls_arr[0], mask=np.ma.getmaskarray(cls_arr[0]))

#         with rasterio.open(acc_path) as acc_ds:
#             same_grid = (acc_ds.crs == hab_ds.crs and
#                          acc_ds.transform == hab_ds.transform and
#                          acc_ds.width == hab_ds.width and
#                          acc_ds.height == hab_ds.height)
#             if same_grid:
#                 acc_arr, _ = rio_mask(acc_ds, [geom_in_raster], crop=False, filled=False)
#                 acc_ma = np.ma.masked_array(acc_arr[0], mask=np.ma.getmaskarray(acc_arr[0]))
#             else:
#                 acc_reproj = np.empty((hab_ds.height, hab_ds.width), dtype=np.float32)
#                 reproject(
#                     source=rasterio.band(acc_ds, 1),
#                     destination=acc_reproj,
#                     src_transform=acc_ds.transform,
#                     src_crs=acc_ds.crs,
#                     dst_transform=hab_ds.transform,
#                     dst_crs=hab_ds.crs,
#                     resampling=Resampling.bilinear,
#                 )
#                 acc_ma = np.ma.masked_array(acc_reproj, mask=cls_ma.mask)

#         px_area_m2 = _pixel_area_m2(hab_ds.transform)
#         px_area_ha = px_area_m2 / 10_000.0

#         inside = ~cls_ma.mask
#         classes = cls_ma.data[inside].astype(np.int64)

#         counts = np.bincount(classes, minlength=4)
#         extent_ha_by_code = counts * px_area_ha

#         acc_filled = np.ma.filled(acc_ma, 0.0)
#         acc_sums_m3yr = np.bincount(classes,
#                                     weights=acc_filled[inside],
#                                     minlength=4) * px_area_m2

#         rows = []
#         for code in ORDER:
#             name = SALTMARSH_MAP[code]
#             extent_ha = round(float(extent_ha_by_code[code]), 2)
#             if code in (0, 1):
#                 acc_val = round(float(acc_sums_m3yr[code]), 2)
#             else:
#                 acc_val = "-"
#             rows.append((name, extent_ha, acc_val))

#     return pd.DataFrame(rows, columns=["Ecosystem", "Extent (ha)", "Accretion (m³/yr)"])





# -------------------- VERSION PARA INTENTAR ARREGLAR PROBLEMAS DE RUTAS EN PRODUCCIÓN --------------------
from typing import Any, List, Optional, Dict
import os
import pandas as pd                                                
import geopandas as gpd                                          
from shapely.geometry import Polygon, shape, MultiPolygon                     
from shapely.ops import unary_union, transform as shp_transform
import numpy as np
from pyproj import Transformer, Geod
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import reproject, Resampling
from rasterio.features import shapes, rasterize
from pathlib import Path
from rasterio.windows import Window, from_bounds


# --- NUEVO: Base path dinámico para producción ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def resolve_path(rel_path: str):
    """Convierte una ruta relativa en una absoluta basada en el directorio del proyecto."""
    if not rel_path:
        return None
    return str(BASE_DIR / rel_path)


EUNIS_PATHS = {
    "Santander":  "results/opsa/Santander/eunis_santander.parquet",     
    "North_Sea":  "results/opsa/North_Sea/eunis_north_sea.parquet",    
    "Irish_Sea":  "results/opsa/Irish_Sea/eunis_irish_sea.parquet",     
}

def eunis_available(area: str) -> bool:                
    return area in EUNIS_PATHS                               

def eunis_path(area: str):
    return resolve_path(EUNIS_PATHS.get(area))

SALTMARSH_PATHS = {
    "Santander": ["results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g.tif", "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g_accretion.tif"],
    "Cadiz_Bay": ["results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g.tif", "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif"],
    "Urdaibai_Estuary": ["results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g.tif", "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g_accretion.tif"]
}

SALTMARSH_SCENARIOS_PATHS = {
    "Santander": {
        "regional_rcp45": {
            "habitats": {
                "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g.tif",
                "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2062_7g.tif",
                "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2112_7g.tif"
            },
            "accretion": {
                "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2012_7g_accretion.tif",
                "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2062_7g_accretion.tif",
                "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp45/santander_reg_rcp45_2112_7g_accretion.tif"
            }
        },
        "regional_rcp85": {
            "habitats": {
                "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp45_2012_7g.tif",
                "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2062_7g.tif",
                "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2112_7g.tif"
            },
            "accretion": {
                "2012": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp45_2012_7g_accretion.tif",
                "2062": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2062_7g_accretion.tif",
                "2112": "results/saltmarshes/Bay_of_Santander/regional_rcp85/santander_reg_rcp85_2112_7g_accretion.tif"
            }
        },
        "global_rcp45":  {
            "habitats": {
                "2012": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_reg_rcp45_2012_7g.tif",
                "2062": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2062_7g.tif",
                "2112": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2112_7g.tif"
            },
            "accretion": {
                "2012": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_reg_rcp45_2012_7g_accretion.tif",
                "2062": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2062_7g_accretion.tif",
                "2112": "results/saltmarshes/Bay_of_Santander/global_rcp45/santander_glo_rcp45_2112_7g_accretion.tif"
            }
        }
    },

    "Cadiz_Bay": {
        "regional_rcp45": {
            "habitats": {
                "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g.tif",
                "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2073_25g.tif",
                "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2123_25g.tif"
            },
            "accretion": {
                "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif",
                "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2073_25g_accretion.tif",
                "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp45/cadiz_reg_rcp45_2123_25g_accretion.tif"
            }
        },
        "regional_rcp85": {
            "habitats": {
                "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp45_2023_25g.tif",
                "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2073_25g.tif",
                "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2123_25g.tif"
            },
            "accretion": {
                "2023": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp45_2023_25g_accretion.tif",
                "2073": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2073_25g_accretion.tif",
                "2123": "results/saltmarshes/Cadiz_Bay/regional_rcp85/cadiz_reg_rcp85_2123_25g_accretion.tif"
            }
        },
        "global_rcp45":  {
            "habitats": {
                "2023": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_reg_rcp45_2023_25g.tif",
                "2073": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2073_25g.tif",
                "2123": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2123_25g.tif"
            },
            "accretion": {
                "2023": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_reg_rcp45_2023_25g_accretion.tif",
                "2073": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2073_25g_accretion.tif",
                "2123": "results/saltmarshes/Cadiz_Bay/global_rcp45/cadiz_glo_rcp45_2123_25g_accretion.tif"
            }
        }
    },

    "Urdaibai_Estuary": {
        "regional_rcp45": {
            "habitats": {
                "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g.tif",
                "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2067_17g.tif",
                "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2117_17g.tif"
            },
            "accretion": {
                "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2017_17g_accretion.tif",
                "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2067_17g_accretion.tif",
                "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp45/oka_reg_rcp45_2117_17g_accretion.tif"
            }
        },
        "regional_rcp85": {
            "habitats": {
                "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp45_2017_17g.tif",
                "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2067_17g.tif",
                "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2117_17g.tif"
            },
            "accretion": {
                "2017": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp45_2017_17g_accretion.tif",
                "2067": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2067_17g_accretion.tif",
                "2117": "results/saltmarshes/Urdaibai_Estuary/regional_rcp85/oka_reg_rcp85_2117_17g_accretion.tif"
            }
        },
        "global_rcp45":  {
            "habitats": {
                "2017": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_reg_rcp45_2017_17g.tif",
                "2067": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2067_17g.tif",
                "2117": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2117_17g.tif"
            },
            "accretion": {
                "2017": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_reg_rcp45_2017_17g_accretion.tif",
                "2067": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2067_17g_accretion.tif",
                "2117": "results/saltmarshes/Urdaibai_Estuary/global_rcp45/oka_glo_rcp45_2117_17g_accretion.tif"
            }
        }
    },
}

def _norm(p): 
    return os.path.normpath(p) if p else None

def saltmarsh_scenario_available(area: str, scenario_key: str) -> bool:
    return bool(SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key))

def saltmarsh_scenario_years(area: str, scenario_key: str):
    node = SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key, {})
    years = list((node.get("habitats") or {}).keys())
    try:
        years = sorted(years, key=lambda y: int(y))
    except Exception:
        years = sorted(years)
    return years

def saltmarsh_scenario_paths(area: str, scenario_key: str, year: str):
    node = SALTMARSH_SCENARIOS_PATHS.get(area, {}).get(scenario_key, {})
    h_rel = _norm((node.get("habitats") or {}).get(year))
    a_rel = _norm((node.get("accretion") or {}).get(year))
    return resolve_path(h_rel), resolve_path(a_rel)

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
    return resolve_path(paths[0]) if paths else None

def saltmarsh_accretion_path(area: str): 
    paths = SALTMARSH_PATHS.get(area)
    return resolve_path(paths[1]) if paths else None

def _collect_activity_union(activity_children, activity_upload_children) -> gpd.GeoDataFrame:
    geoms = []
    if activity_children:
        for ch in (activity_children if isinstance(activity_children, list) else [activity_children]):
            if isinstance(ch, dict) and ch.get("type", "").endswith("Polygon"):
                pos = (ch.get("props", {}) or {}).get("positions") or []
                if pos and len(pos) >= 3:
                    ring = [(float(lon), float(lat)) for lat, lon in pos] 
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
    gdf["geometry"] = gdf.buffer(0) 
    return gdf

def activity_eunis_table(area: str,
                     activity_children,
                     activity_upload_children,
                     label_col: str) -> pd.DataFrame:
    geoms = []
    if activity_children:
        for ch in (activity_children if isinstance(activity_children, list) else [activity_children]):
            if isinstance(ch, dict) and ch.get("type","").endswith("Polygon"):
                pos = (ch.get("props",{}) or {}).get("positions") or []
                if pos and len(pos) >= 3:
                    ring = [(float(lon), float(lat)) for lat, lon in pos]
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
    act["geometry"] = act.buffer(0) 

    p = eunis_path(area)
    if not p:
        return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])
    eunis = gpd.read_parquet(p) if p.lower().endswith(".parquet") else gpd.read_file(p)
    eunis = eunis.to_crs(4326) if eunis.crs else eunis.set_crs(4326)
    eunis["geometry"] = eunis.buffer(0)

    if not label_col:
        raise ValueError("Debes pasar 'label_col' con el nombre de la columna de hábitat.")
    cols_map = {c.lower(): c for c in eunis.columns}
    label_key = cols_map.get(label_col.lower()) 
    if not label_key:
        raise KeyError(f"Columna '{label_col}' no existe en EUNIS. Columnas disponibles: {list(eunis.columns)}")

    cond_col = "condition" if "condition" in eunis.columns else ("Condition" if "Condition" in eunis.columns else None)
    keep_cols = [label_key, "geometry"] + ([cond_col] if cond_col else [])
    eunis_sub = eunis[keep_cols].copy()

    try:
        inter = gpd.overlay(eunis_sub, act[["geometry"]], how="intersection")
    except Exception:
        inter = gpd.overlay(eunis_sub.buffer(0), act.buffer(0)[["geometry"]], how="intersection")

    if inter.empty:
        return pd.DataFrame(columns=["EUNIS habitat","Extent (km²)","Condition"])

    inter_m = inter.to_crs(3035)
    inter["area_km2"] = inter_m.area / 1e6

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

def _pixel_area_m2(transform) -> float:
    return abs(transform.a * transform.e - transform.b * transform.d)

def activity_saltmarsh_table(area: str,
                             activity_children,
                             activity_upload_children) -> pd.DataFrame:
    ORDER = [0, 1, 2, 3] 

    act = _collect_activity_union(activity_children, activity_upload_children)
    if act.empty:
        return pd.DataFrame({
            "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
            "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
            "Accretion (m³/yr)": [0.0, 0.0, "-", "-"], 
        })

    hab_path = saltmarsh_habitat_path(area)
    acc_path = saltmarsh_accretion_path(area)
    if not hab_path or not acc_path:
        raise ValueError(f"No hay TIFFs de saltmarsh para el área '{area}'.")

    with rasterio.open(hab_path) as hab_ds:
        if hab_ds.crs is None or hab_ds.crs.is_geographic:
            raise ValueError("El TIFF de hábitat debe tener un CRS proyectado (en metros).")

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
        acc_sums = np.bincount(classes,
                               weights=acc_filled[inside],
                               minlength=4) * px_area_m2

        rows = []
        for code in ORDER:
            name = SALTMARSH_MAP[code]
            extent_ha = round(float(extent_ha_by_code[code]), 2)
            if code in (0, 1): 
                acc_val = round(float(acc_sums[code]), 2)
            else:
                acc_val = "-"
            rows.append((name, extent_ha, acc_val))

    return pd.DataFrame(rows, columns=["Ecosystem", "Extent (ha)", "Accretion (m³/yr)"])

def activity_saltmarsh_scenario_table(area: str,
                                      scenario_key: str,
                                      year: str,
                                      activity_children,
                                      activity_upload_children) -> pd.DataFrame:
    ORDER = [0, 1, 2, 3]

    act = _collect_activity_union(activity_children, activity_upload_children)
    if act.empty:
        return pd.DataFrame({
            "Ecosystem": [SALTMARSH_MAP[c] for c in ORDER],
            "Extent (ha)": [0.0, 0.0, 0.0, 0.0],
            "Accretion (m³/yr)": [0.0, 0.0, "-", "-"],
        })

    hab_path, acc_path = saltmarsh_scenario_paths(area, scenario_key, year)
    if not (hab_path and acc_path):
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


# -------------------------------------------------------------------------
# --- FISH STOCKS LOGIC ---
# -------------------------------------------------------------------------

FISH_PRES_ABS_BASE = "results/pelagic_fish_stocks/presence_absence"
FISH_ACCOUNTS_PATH = "results/pelagic_fish_stocks/SPF_accounts_MESIT.parquet"

STOCKS_CONFIG = {
    'ANE8':   {'taxon': 'taxonid=126426', 'res': ''},
    'ANE9AS': {'taxon': 'taxonid=126426', 'res': ''},
    'PIL8C9A': {'taxon': 'taxonid=126421', 'res': ''},
    'HOM9A':   {'taxon': 'taxonid=126822', 'res': '0_05deg'},
    'HOMNEA':  {'taxon': 'taxonid=126822', 'res': '0_25deg'},
    'MACNEA':  {'taxon': 'taxonid=127023', 'res': ''}
}

# def _get_affected_extent_km2(geom_4326, stock_id, period_key):
#     """Calcula el extent (km2) extrayendo polígonos y proyectando a métrico (EPSG:3035)."""
#     config = STOCKS_CONFIG.get(stock_id)
#     if not config: return 0.0
    
#     res_suffix = f"_{config['res']}" if config['res'] else ""
#     rel_path = f"{FISH_PRES_ABS_BASE}/{config['taxon']}/method=ensemble/threshold=max_spec_sens/{period_key}{res_suffix}.tif"
#     tif_path = resolve_path(rel_path)
    
#     if not tif_path or not os.path.exists(tif_path):
#         return 0.0

#     with rasterio.open(tif_path) as src:
#         if src.crs:
#             project = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
#             geom_raster_crs = shp_transform(project, geom_4326)
#         else:
#             geom_raster_crs = geom_4326
        
#         try:
#             out_image, out_transform = rio_mask(src, [geom_raster_crs], crop=True, filled=True)
            
#             # Crear una máscara binaria estricta (1 = presencia, el resto a 0)
#             mask_presence = (out_image[0] == 1).astype('uint8')
            
#             if np.sum(mask_presence) == 0:
#                 return 0.0
            
#             # Extraer las geometrías exactas de los píxeles
#             polygons = []
#             for geom, val in shapes(mask_presence, transform=out_transform):
#                 if val == 1:
#                     polygons.append(shape(geom))
                    
#             if not polygons:
#                 return 0.0
                
#             # Convertir a GeoDataFrame y reproyectar a EPSG:3035 para área métrica europea
#             gdf_presence = gpd.GeoDataFrame(geometry=polygons, crs=src.crs or "EPSG:4326")
#             if gdf_presence.crs.is_geographic:
#                 gdf_presence = gdf_presence.to_crs("EPSG:3035")
                
#             # Sumar área y convertir a km²
#             return float(gdf_presence.area.sum() / 1e6)
#         except Exception as e:
#             print(f"Error calculating fish overlap for {stock_id}: {e}")
#             return 0.0



def _get_affected_extent_km2(geom_4326, stock_id, period_key):
    """
    Calcula el área (km2) exacta mediante la vectorización de la intersección 
    entre el área de interés, el stock y la presencia (SDM).
    """
    config = STOCKS_CONFIG.get(stock_id)
    if not config: 
        return 0.0
    
    # 1. Validación de rutas y carga de límites del Stock (Filtro espacial rápido)
    stock_parquet_path = resolve_path(f"results/pelagic_fish_stocks/{stock_id.lower()}.parquet")
    if not stock_parquet_path or not os.path.exists(stock_parquet_path):
        return 0.0
        
    try:
        stock_gdf = gpd.read_parquet(stock_parquet_path)
        if stock_gdf.crs is None or stock_gdf.crs.to_string() != "EPSG:4326":
            stock_gdf = stock_gdf.to_crs("EPSG:4326")
            
        minx, miny, maxx, maxy = geom_4326.bounds
        stock_bounds = stock_gdf.total_bounds
        
        # Filtro Bounding Box: Si no hay contacto entre cajas, área es 0
        if not (minx <= stock_bounds[2] and maxx >= stock_bounds[0] and
                miny <= stock_bounds[3] and maxy >= stock_bounds[1]):
            return 0.0
    except Exception as e:
        print(f"Error en filtro inicial para {stock_id}: {e}")
        return 0.0
        
    # 2. Localización del Raster (SDM)
    res_suffix = f"_{config['res']}" if config['res'] else ""
    rel_path = f"{FISH_PRES_ABS_BASE}/{config['taxon']}/method=ensemble/threshold=max_spec_sens/{period_key}{res_suffix}.tif"
    tif_path = resolve_path(rel_path)
    
    if not tif_path or not os.path.exists(tif_path):
        return 0.0

    with rasterio.open(tif_path) as src:
        # Ajuste de coordenadas si el raster no es 4326
        if src.crs and src.crs.to_string() != "EPSG:4326":
            t = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            rminx, rminy = t.transform(minx, miny)
            rmaxx, rmaxy = t.transform(maxx, maxy)
            rminx, rmaxx = min(rminx, rmaxx), max(rminx, rmaxx)
            rminy, rmaxy = min(rminy, rmaxy), max(rminy, rmaxy)
            geom_raster_coord = shp_transform(t.transform, geom_4326)
            stock_raster_coord = stock_gdf.to_crs(src.crs)
        else:
            rminx, rminy, rmaxx, rmaxy = minx, miny, maxx, maxy
            geom_raster_coord = geom_4326
            stock_raster_coord = stock_gdf
            
        # Definición de la Ventana de lectura (Window)
        window = from_bounds(rminx, rminy, rmaxx, rmaxy, src.transform)
        window = window.intersection(Window(0, 0, src.width, src.height))
        
        if window.width <= 0 or window.height <= 0:
            return 0.0
            
        window = window.round_offsets().round_lengths()
        tif_data = src.read(1, window=window)
        win_transform = src.window_transform(window)
        
        try:
            # --- CAPA 1: Máscara del usuario ---
            geoms = [geom_raster_coord] if geom_raster_coord.geom_type == 'Polygon' else list(geom_raster_coord.geoms)
            user_mask = rasterize([(g, 1) for g in geoms], out_shape=tif_data.shape, 
                                  transform=win_transform, fill=0, dtype='uint8')
            
            # --- CAPA 2: Máscara del Stock (Clipped) ---
            stock_sub = stock_raster_coord.cx[rminx:rmaxx, rminy:rmaxy]
            if stock_sub.empty: return 0.0
            stock_mask = rasterize([(g, 1) for g in stock_sub.geometry], out_shape=tif_data.shape, 
                                   transform=win_transform, fill=0, dtype='uint8')
            
            # --- CAPA 3: Intersección Final (AND lógico) ---
            # Solo píxeles donde (User=1) AND (Stock=1) AND (Presence=1)
            final_mask = ((user_mask == 1) & (stock_mask == 1) & (tif_data == 1)).astype('uint8')
            
            if not np.any(final_mask):
                return 0.0
                
            # --- VECTORIZACIÓN Y CÁLCULO GEODÉSICO ---
            # 1. Convertimos los píxeles resultantes a geometrías vectoriales
            shapes_gen = shapes(final_mask, mask=(final_mask == 1), transform=win_transform)
            
            # 2. Construimos una lista de polígonos
            polygons = [shape(s) for s, v in shapes_gen]
            
            if not polygons:
                return 0.0
            
            # 3. Creamos un MultiPolygon (maneja naturalmente el multipart)
            presence_geometry = MultiPolygon(polygons)
            
            # 4. Calculamos el área geodésica exacta en WGS84
            geod = Geod(ellps="WGS84")
            area_m2, _ = geod.geometry_area_perimeter(presence_geometry)
            
            return abs(area_m2) / 1e6 # Retorno en km2
            
        except Exception as e:
            print(f"Error en procesamiento espacial para {stock_id}: {e}")
            return 0.0

def activity_fish_table(area: str, activity_children, activity_upload_children) -> pd.DataFrame:
    """Calcula el impacto anual en peces, agrupando en un resumen '-' si el extent es 0."""
    act_gdf = _collect_activity_union(activity_children, activity_upload_children)
    if act_gdf.empty:
        return pd.DataFrame()

    geom = act_gdf.geometry.iloc[0]
    df_accounts = pd.read_parquet(resolve_path(FISH_ACCOUNTS_PATH))
    results = []
    
    for stock_id in STOCKS_CONFIG.keys():
        df_stock = df_accounts[df_accounts['Stock'] == stock_id]
        if df_stock.empty:
            continue
            
        # --- PERIODO 1: 2000-2009 ---
        ext_00_09 = _get_affected_extent_km2(geom, stock_id, "2000_2010")
        if ext_00_09 == 0:
            results.append({
                "Stock": stock_id,
                "Year": "2000-2009",
                "Extent affected (km²)": "-",
                "Condition (0-1)": "-",
                "FP Supply affected (tons)": "-"
            })
        else:
            for year in range(2000, 2010):
                row = df_stock[df_stock['Year'] == year]
                if not row.empty:
                    r = row.iloc[0]
                    total_extent_year = r['Extent']
                    proportion = ext_00_09 / total_extent_year if total_extent_year > 0 else 0
                    results.append({
                        "Stock": stock_id,
                        "Year": str(year),
                        "Extent affected (km²)": round(ext_00_09, 2),
                        "Condition (0-1)": round(r['Condition'], 3) if pd.notnull(r['Condition']) else "-",
                        "FP Supply affected (tons)": round(r['FP_supply'] * proportion, 2)
                    })
                    
        # --- PERIODO 2: 2010-2019 ---
        ext_10_19 = _get_affected_extent_km2(geom, stock_id, "2010_2020")
        if ext_10_19 == 0:
            results.append({
                "Stock": stock_id,
                "Year": "2010-2019",
                "Extent affected (km²)": "-",
                "Condition (0-1)": "-",
                "FP Supply affected (tons)": "-"
            })
        else:
            for year in range(2010, 2020):
                row = df_stock[df_stock['Year'] == year]
                if not row.empty:
                    r = row.iloc[0]
                    total_extent_year = r['Extent']
                    proportion = ext_10_19 / total_extent_year if total_extent_year > 0 else 0
                    results.append({
                        "Stock": stock_id,
                        "Year": str(year),
                        "Extent affected (km²)": round(ext_10_19, 2),
                        "Condition (0-1)": round(r['Condition'], 3) if pd.notnull(r['Condition']) else "-",
                        "FP Supply affected (tons)": round(r['FP_supply'] * proportion, 2)
                    })

    return pd.DataFrame(results)