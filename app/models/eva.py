from __future__ import annotations
import os  
import json  
from typing import List, Tuple, Dict  
import numpy as np  
import pandas as pd  
import geopandas as gpd 
from pyproj import CRS
import shapely
from shapely.geometry import box
from shapely import wkb, wkt
import matplotlib.pyplot as plt

# --------------------- START CODE TO COMPUTE EVA AQs USING OBIS CLIENT --------------------------------------


# Some useful functions to process the data:

# Function to find the best UTM CRS in case the user aoi has a non proyected CRS
def best_utm_crs(file:str) -> CRS:
    """Elige una UTM en función del centroide (lat/lon)."""
    if file.endswith(".parquet"):
        gdf= gpd.read_parquet(file)
    elif file.endswith(".json"):
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


# --------------------- EVA Assessment Questions ----------------------------------------------------
def aq1(
     aoi: str,                      # ruta al area de interes (json o parquet)
     #species: List[str],            # list of Worms species ID  or species name
     grid_size: int                # size of the rectangular grid in meters  
     #min_grid_per: int,             # minimum percercentage of grids that need to have data to do the assessment (computed with each species).
     #cut_lrf: int                   # threshold percentage used to define a species as Locally Rare Species. Less or equal to this threshold will be defined as Locally Rare.
    ) -> json:

    # We add a conditional to check file format
    if not (aoi.endswith(".json") or aoi.endswith(".parquet")):
        raise ValueError("The selected file is not a .json or .parquet file!")
    
    # Read the file:
    if aoi.endswith(".parquet"):
        aoi_gdf= gpd.read_parquet(aoi)
    elif aoi.endswith(".json"):
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

    filtered_grid.to_file(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\cleaned_grid.shp")
    

    #print(f"Min longitude: {min_x}; Min latitude {min_y}; Max longitude: {max_x}; Max latitude: {max_y}")

    # Create a regular grid with the bbox coordinates and the gridsize passed by the user:


    return print(json.dumps("//"))

aq1(r"C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\opsa\Santander\eunis_santander.parquet", 3000)