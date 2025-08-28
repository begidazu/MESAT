from __future__ import annotations
import os, json
from datetime import datetime
from datetime import timedelta 
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Dict, Union, Iterable 
import numpy as np  
import pandas as pd  
import geopandas as gpd 
from pyproj import CRS
import shapely
from shapely.geometry import box, Point, Polygon, MultiPolygon, GeometryCollection
from shapely import wkb, wkt
import matplotlib.pyplot as plt
from pyobis.occurrences import occurrences
try:
    from shapely.validation import make_valid   # Shapely ≥2.0
    _has_make_valid = True
except Exception:
    _has_make_valid = False

# --------------------- START CODE TO COMPUTE EVA AQs USING OBIS CLIENT --------------------------------------


# Some useful functions to process the data:

# Function to find the best UTM CRS in case the user aoi has a non proyected CRS
def best_utm_crs(file:str) -> CRS:
    """Elige una UTM en función del centroide (lat/lon)."""
    if file.endswith(".parquet"):
        gdf= gpd.read_parquet(file)
    elif (file.endswith(".json") or file.endswith(".geojson")):
        gdf = gpd.read_file(file)
    g_ll = gdf.to_crs(4326) if (gdf.crs and gdf.crs.to_epsg() != 4326) else gdf
    c = g_ll.unary_union.centroid
    lon, lat = c.x, c.y
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)

# Function to create a regular grid:
def create_grid(gdf = None, bounds=None, grid_size = 100):
    """Create square grid that covers a geodataframe area
    or a fixed boundary with x-y coords
    returns: a GeoDataFrame of grid polygons
    see https://james-brennan.github.io/posts/fast_gridding_geopandas/
    """
    # bounds:
    xmin, ymin, xmax, ymax= bounds
    # cell size
    cell_size = grid_size
    # Geodataframe CRS:
    crs = gdf.crs
    # create the cells in a loop
    grid_cells = []
    for x0 in np.arange(xmin, xmax+cell_size, cell_size ):
        for y0 in np.arange(ymin, ymax+cell_size, cell_size):
            x1 = x0-cell_size
            y1 = y0+cell_size
            poly = shapely.geometry.box(x0, y0, x1, y1)
            #print (gdf.overlay(poly, how='intersection'))
            grid_cells.append( poly )
    cells = gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs=crs)
    return cells

# Funcion para quedarnos con los poligonos de un Geodataframe que intersecan con otro Geodataframe
def keep_intersecting(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # 1) Sanea geometrías (evita TopologyException)
    g1 = gdf1.copy()
    g2 = gdf2.copy()
    g1["geometry"] = g1.geometry.buffer(0)
    g2["geometry"] = g2.geometry.buffer(0)

    # 2) Une espacialmente y conserva índices únicos de la izquierda
    hits = gpd.sjoin(g1, g2[["geometry"]], how="inner", predicate="intersects")
    return g1.loc[hits.index.unique()].copy() 

def to_multipolygon(obj: Union[gpd.GeoDataFrame, gpd.GeoSeries, Polygon, MultiPolygon, GeometryCollection, Iterable]) -> MultiPolygon:
    """Devuelve siempre un MultiPolygon a partir de Polygon/MultiPolygon/Geo(Series|DataFrame)/lista."""
    # 1) recopila geometrías
    if isinstance(obj, gpd.GeoDataFrame):
        geoms = obj.geometry
    elif isinstance(obj, gpd.GeoSeries):
        geoms = obj
    elif isinstance(obj, (Polygon, MultiPolygon, GeometryCollection)):
        geoms = [obj]
    elif isinstance(obj, Iterable):
        geoms = obj
    else:
        raise TypeError("Objeto no soportado para to_multipolygon().")

    # 2) sanea y conserva solo polígonos
    polys = []
    for g in geoms:
        if g is None:
            continue
        if _has_make_valid:
            g = make_valid(g)
        else:
            g = g.buffer(0)
        if g.is_empty:
            continue
        if g.geom_type == "Polygon":
            polys.append(g)
        elif g.geom_type == "MultiPolygon":
            polys.extend(list(g.geoms))
        elif g.geom_type == "GeometryCollection":
            for part in g.geoms:
                if part.geom_type == "Polygon":
                    polys.append(part)
                elif part.geom_type == "MultiPolygon":
                    polys.extend(list(part.geoms))

    if not polys:
        return MultiPolygon([])

    # 3) disolver y asegurar MultiPolygon (compatible con versiones)
    try:
        from shapely import union_all as shp_union_all  # Shapely 2.x rápido
        merged = shp_union_all(polys)
    except Exception:
        from shapely.ops import unary_union as shp_unary_union  # fallback
        merged = shp_unary_union(polys)

    if merged.geom_type == "Polygon":
        return MultiPolygon([merged])
    if merged.geom_type == "MultiPolygon":
        return merged

    # Colección rara: extrae lo areal
    parts = []
    for part in getattr(merged, "geoms", []):
        if part.geom_type == "Polygon":
            parts.append(part)
        elif part.geom_type == "MultiPolygon":
            parts.extend(list(part.geoms))
    return MultiPolygon(parts) if parts else MultiPolygon([])


# --------------------- EVA Assessment Questions ----------------------------------------------------
def aq1(
     aoi: str,                       # ruta al area de interes (json o parquet)
     species: List[str],             # list of species names
     grid_size: int,                  # size of the rectangular grid in meters  
     #min_grid_per: int,             # minimum percercentage of grids that need to have data to do the assessment (computed with each species).
     #cut_lrf: int,                   # threshold percentage used to define a species as Locally Rare Species. Less or equal to this threshold will be defined as Locally Rare.
     span_years: int                  # Time span of the occurrence data for the assesment in years
    ) -> json:

    # We add a conditional to check file format
    if not (aoi.endswith(".json") or aoi.endswith(".parquet") or aoi.endswith(".geojson")):
        raise ValueError("The selected file is not a .json or .parquet file!")
    
    # Read the file:
    if aoi.endswith(".parquet"):
        aoi_gdf= gpd.read_parquet(aoi)
    elif aoi.endswith(".json"):
        aoi_gdf = gpd.read_file(aoi)
    elif aoi.endswith(".geojson"):
        aoi_gdf = gpd.read_file(aoi)

    # Ensure a projected CRS (meters)
    if aoi_gdf.crs.is_projected:
        gdf_m = aoi_gdf
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)
        gdf_m = aoi_gdf.to_crs(metric_crs)

    # Get bounding box of the file
    min_x, min_y, max_x, max_y = gdf_m.total_bounds
    bounds = (min_x, min_y, max_x, max_y)

    # Create the grid for the assessment:
    grid = create_grid(gdf = gdf_m, bounds=bounds, grid_size= grid_size)

    # Clean the grid saving those grids that intersect with the aoi:
    filtered_grid = keep_intersecting(grid, gdf_m)

    # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

        # Dissolve AOI and normalize to MultiPolygon and get the wkt:
    # gdf_m_wgs = gdf_m.to_crs(epsg=4326)
    # geom_all = gdf_m_wgs.geometry.union_all() if hasattr(gdf_m_wgs.geometry, "union_all") else gdf_m_wgs.unary_union
    # mp = to_multipolygon(geom_all)
    
    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = aoi_gdf.to_crs(epsg=4326)
    geom = aoi_gdf.geometry.iloc[0]
    geom_s = geom.simplify(0.005, preserve_topology=True)
    wkt_str = wkt_dumps(geom_s, rounding_precision=6)
    
        # Download accourrences
    occ_data = occurrences.search(scientificname=species, geometry=wkt_str, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()
    print(occ_data)
    print(occ_data.columns)
    # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
    fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
    fil_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

    # Create geometry of the occurrence data
    geometry = [Point(xy) for xy in zip(fil_occ_data['decimalLongitude'], fil_occ_data['decimalLatitude'])]

    # Create the occurrence geodataframe:
    occ_gdf = gpd.GeoDataFrame(fil_occ_data, geometry=geometry)

    # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
    occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

    # Project the occ_gdf into the aoi CRS:
    occ_gdf_proj = occ_gdf.to_crs(metric_crs)

    occ_gdf_proj.to_file(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\test_occurrence.shp")

    #print(f"Min longitude: {min_x}; Min latitude {min_y}; Max longitude: {max_x}; Max latitude: {max_y}")

    # Create a regular grid with the bbox coordinates and the gridsize passed by the user:


    return print(json.dumps("//"))

aq1(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\cantabria_test.geojson", ["Spartina", "Juncus"], 3000, 50)