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
def best_utm_crs(aoi:None) -> CRS:
    """Elige una UTM en función del centroide (lat/lon)."""
    # if file.endswith(".parquet"):
    #     gdf= gpd.read_parquet(file)
    # elif (file.endswith(".json") or file.endswith(".geojson")):
    #     gdf = gpd.read_file(file)
    if isinstance(aoi, gpd.GeoDataFrame):
        aoi_gdf = aoi
    # --- 2. Si es ruta a fichero ---
    elif isinstance(aoi, str):
        if not (aoi.endswith(".json") or aoi.endswith(".parquet") or aoi.endswith(".geojson")):
            raise ValueError("The selected file is not a supported format (.json, .geojson, .parquet)")
        if aoi.endswith(".parquet"):
            aoi_gdf = gpd.read_parquet(aoi)
        else:
            aoi_gdf = gpd.read_file(aoi)
    else:
        raise TypeError("Parameter 'aoi' must be a GeoDataFrame or a path to a supported file")
    
    g_ll = aoi_gdf.to_crs(4326) if (aoi_gdf.crs and aoi_gdf.crs.to_epsg() != 4326) else aoi_gdf
    c = g_ll.unary_union.centroid
    lon, lat = c.x, c.y
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)

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

# Function to create a regular grid:
def create_grid(aoi = None, grid_size = 1000):
    """Create square grid that covers the area of interest
    returns: a GeoDataFrame of grid polygons
    """

    # # We add a conditional to check file format
    # if not (aoi.endswith(".json") or aoi.endswith(".parquet") or aoi.endswith(".geojson")):
    #     raise ValueError("The selected file is not a .json or .parquet file!")
    
    # # Read the file:
    # if aoi.endswith(".parquet"):
    #     aoi_gdf= gpd.read_parquet(aoi)
    # elif aoi.endswith(".json"):
    #     aoi_gdf = gpd.read_file(aoi)
    # elif aoi.endswith(".geojson"):
    #     aoi_gdf = gpd.read_file(aoi)

    if isinstance(aoi, gpd.GeoDataFrame):
        aoi_gdf = aoi
    # --- 2. Si es ruta a fichero ---
    elif isinstance(aoi, str):
        if not (aoi.endswith(".json") or aoi.endswith(".parquet") or aoi.endswith(".geojson")):
            raise ValueError("The selected file is not a supported format (.json, .geojson, .parquet)")
        if aoi.endswith(".parquet"):
            aoi_gdf = gpd.read_parquet(aoi)
        else:
            aoi_gdf = gpd.read_file(aoi)
    else:
        raise TypeError("Parameter 'aoi' must be a GeoDataFrame or a path to a supported file")


    # Ensure a projected CRS (meters)
    if aoi_gdf.crs.is_projected:
        gdf_m = aoi_gdf
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)
        gdf_m = aoi_gdf.to_crs(metric_crs)

    # bounds:
    min_x, min_y, max_x, max_y = gdf_m.total_bounds
    bounds = (min_x, min_y, max_x, max_y)

    # cell size
    cell_size = grid_size
    # Geodataframe CRS:
    crs = aoi_gdf.crs
    # create the cells in a loop
    grid_cells = []
    for x0 in np.arange(min_x, max_x+cell_size, cell_size ):
        for y0 in np.arange(min_y, max_y+cell_size, cell_size):
            x1 = x0-cell_size
            y1 = y0+cell_size
            poly = shapely.geometry.box(x0, y0, x1, y1)
            #print (gdf.overlay(poly, how='intersection'))
            grid_cells.append( poly )
    cells = gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs=metric_crs)

    filtered_cells = keep_intersecting(cells, gdf_m)
    return filtered_cells

def to_multipolygon(obj: Union[gpd.GeoDataFrame, gpd.GeoSeries, Polygon, MultiPolygon, GeometryCollection, Iterable]) -> MultiPolygon:
    """Returns always a MultiPolygon from Polygon/MultiPolygon/Geo(Series/Dataframe)/list."""
    # 1) Geometries
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

    # 2) Sanitize and keep just the polygons
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

    # 3) Dissolve and ensure Multipolygon
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

# Function to get the WKT string annd geodataframe of the selected coutirries EEZ:
def country_eez(
        country_name:str
) -> Tuple[str, gpd.GeoDataFrame]:
    eez_path = r"./results/EVA/world_eez.parquet"
    eez_file = gpd.read_parquet(eez_path)
    filtered_eez = eez_file[eez_file.SOVEREIGN1 == country_name]

    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = filtered_eez.to_crs(epsg=4326)
    # geom = aoi_gdf.geometry.iloc[0]
    # geom_s = geom.simplify(0.005, preserve_topology=True)

    minx, miny, maxx, maxy = aoi_gdf.total_bounds

    bbox = box(minx, miny, maxx, maxy)

    wkt_str = wkt_dumps(bbox, rounding_precision=6)

    return wkt_str, filtered_eez



# --------------------- EVA Assessment Questions ----------------------------------------------------

# Assessment Question 1: presence of Locally Rare Features
def locally_rare_features_presence(
     aoi: str,                       # ruta al area de interes (json o parquet)
     species: List[str],             # list of species names
     assessment_grid: gpd.GeoDataFrame,
     min_grid_per: int,             # minimum percercentage of grids that need to have data to do the assessment (computed with each species).
     cut_lrf: int,                   # threshold percentage used to define a species as Locally Rare Species. Less or equal to this threshold will be defined as Locally Rare.
     span_years: int                  # Time span of the occurrence data for the assesment in years
    ) -> gpd.GeoDataFrame:

    """
    This function computes the EVA Assessment Question 1 from OBIS ocurrence data based on the list of species specified by the user in the area of interest and adds the indicator score to the grid passes by the user.

        Params:
            aoi: area of interest. It has to be in json, geojson or parquet format.
            species: a list of species with the species/genus/family names to take into acount in the assessment. Example: ["Spartina", "Halimione portulacoides", "Anas"].
            grid: grid where the assessment will be conducted and the indicator added.
            min_grid_per: minimum percercentage of grids that need to have data to do the assessment (computed with each species).
            cut_lrf: threshold percentage used to define a species as Locally Rare Species. Less or equal to this threshold will be defined as Locally Rare.
            span_years: Time span of the occurrence data for the assesment in years.

        Returns:
        A gpd.GeoDataFrame with the grid passed by the user and a columns 'aq1' with the Locally Rare Feature condition indicator.

    """

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
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)

    # Set up the occurrence data start and end date:
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    # Convert Area of Interest to 4326 EPSG as obis data is mainly on that Coordinate System. Also simplify the polygon.
    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = aoi_gdf.to_crs(epsg=4326)
    geom = aoi_gdf.geometry.iloc[0]
    geom_s = geom.simplify(0.005, preserve_topology=True)
    wkt_str = wkt_dumps(geom_s, rounding_precision=6)
    
    # Array to store the Locally Rare Species:
    lrs_array = []

    # Create a column where we will aggregate the EV values of Locally Rare Species:
    assessment_grid["aggregation"] = 0

    # Bucle para iterar sobre la lista de especies y definir si son LRF o no:
    for specie in species:

        # Intentamos bajarnos los datos, si no hay datos de esa especie pasamos a la siguiente especie:
        try:
            # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
            occ_data = occurrences.search(scientificname=specie, geometry=wkt_str, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()

            # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
            fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
            filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

            # Create geometry of the occurrence data
            geometry = [Point(xy) for xy in zip(filtered_occ_data['decimalLongitude'], filtered_occ_data['decimalLatitude'])]

            # Create the occurrence geodataframe:
            occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)

            # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
            occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

            # Project the occ_gdf into the aoi CRS:
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            # Grid intersecting with occurrence:
            intersect = gpd.sjoin(assessment_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            occ_grid = assessment_grid.loc[intersect.index.unique()].copy()

            # If the percentage is less than the threshold to do the assessment pass:
            print(f"Numero de grids {specie}:{len(assessment_grid)}; Numero de grids con occurrence data {specie}: {len(occ_grid)}")
            if ((len(occ_grid)/len(assessment_grid))*100) < min_grid_per:
                print(f"El porcentaje de celdas con datos es demasiado pequeno para hacer el assessment con {specie}. Continuamos con la siguinte especie!")
                continue
            elif ((len(occ_grid)/len(assessment_grid))*100) >= min_grid_per:
                print(f"El porcentaje de celdas con datos es adecuado, la especie {specie} se incluye en el assessment")

                # Check if the species is Locally Rare Species or not based on the threshold passed by the user:
                if ((len(occ_grid)/len(assessment_grid))*100) < cut_lrf:
                    print(f"La especie/taxon {specie} es Locally Rare Feature!")
                    lrs_array.append(specie)

                    # Add a value of 5 into a column 'aggregation' where the the especies is present
                    assessment_grid.loc[occ_grid.index, "aggregation"] += 5
                    continue

                elif ((len(occ_grid)/len(assessment_grid))*100) >= cut_lrf:
                    print(f"La especie/taxon {specie} NO es Locally Rare Feature!")
                    continue

        except KeyError:
            pass

    # Average the value with the number of Locally Rare Features
    assessment_grid['aq1'] = assessment_grid["aggregation"]/len(lrs_array)

    return assessment_grid


# Testing AQ1:
aoi = r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\cantabria.geojson"
grid_size = 5000
grid = create_grid(aoi = aoi, grid_size=grid_size)


# Assessment Question 2: abundance of Locally Rare Features (I could not find the way of retrieving abundance data from pyobis)
def aq2(): return 

# Assessment Question 5: presence of Nationally Rare Features/Species
def nationally_rare_feature_presence(
    aoi: str,
    species: List[str],
    country_name: str,
    grid_size:int,
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,             # minimum percercentage of grids that need to have data to do the assessment (computed with each species).
    cut_nrf: int,                   # threshold percentage used to define a species as Locally Rare Species. Less or equal to this threshold will be defined as Locally Rare.
    span_years: int 

) -> gpd.GeoDataFrame:
    
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
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)
    
    # Get EEZ WKT and geodataframe. The EEZ WKT is the BBOX of the EEZ to not break the OBIS API
    eez_wkt, eez_gdf = country_eez(country_name=country_name)

    # Create the grid on the EEZ area
    eez_grid = create_grid(eez_gdf, grid_size=grid_size)

    # Project eez_grid:
    eez_grid = eez_grid.to_crs(metric_crs)

    # Set up the occurrence data start and end date:
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    # Array to store the Nationally Rare Species:
    nrs_array = []

    # Restore the column 'aggregation' where we will aggregate the EV values of Nationally Rare Species:
    assessment_grid["aggregation"] = 0

    # Bucle para iterar sobre la lista de especies y definir si son LRF o no:
    for specie in species:

        # Intentamos bajarnos los datos, si no hay datos de esa especie pasamos a la siguiente especie:
        try:
            # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
            occ_data = occurrences.search(scientificname=specie, geometry=eez_wkt, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()

            # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
            fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
            filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

            # Create geometry of the occurrence data
            geometry = [Point(xy) for xy in zip(filtered_occ_data['decimalLongitude'], filtered_occ_data['decimalLatitude'])]

            # Create the occurrence geodataframe:
            occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)

            # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
            occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

            # Project the occ_gdf into the aoi CRS:
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            # Grid intersecting with occurrence:
            eez_intersect = gpd.sjoin(eez_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            eez_occ_grid = eez_grid.loc[eez_intersect.index.unique()].copy()

            # If the percentage is less than the threshold to do the assessment pass:
            print(f"Numero de grids {specie}:{len(eez_grid)}; Numero de grids con occurrence data {specie}: {len(eez_occ_grid)}")
            if ((len(eez_occ_grid)/len(eez_grid))*100) < min_grid_per:
                print(f"El porcentaje de celdas con datos es demasiado pequeno para hacer el assessment con {specie}. Continuamos con la siguinte especie!")
                continue
            elif ((len(eez_occ_grid)/len(eez_grid))*100) >= min_grid_per:
                print(f"El porcentaje de celdas con datos es adecuado, la especie {specie} se incluye en el assessment")

                # Check if the species is Nationally Rare Species or not based on the threshold passed by the user:
                if ((len(eez_occ_grid)/len(eez_grid))*100) < cut_nrf:
                    print(f"La especie/taxon {specie} es Nationally Rare Feature!")
                    nrs_array.append(specie)

                    # Add a value of 5 into a column 'aggregation' where the the especies is present in the AOI grid
                    intersect = gpd.sjoin(assessment_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
                    occ_grid = assessment_grid.loc[intersect.index.unique()].copy()
                    assessment_grid.loc[occ_grid.index, "aggregation"] += 5
                    continue

                elif ((len(eez_occ_grid)/len(eez_grid))*100) >= cut_nrf:
                    print(f"La especie/taxon {specie} NO es Nationally Rare Feature!")
                    continue

        except KeyError:
            pass

    # Average the value with the number of Locally Rare Features
    assessment_grid['aq5'] = assessment_grid["aggregation"]/len(nrs_array)

    return  assessment_grid

# Assessment Question 7: Feature number presence-absence
def feature_number_presence(
    aoi: str,
    species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    span_years: int
) -> gpd.GeoDataFrame:
    
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
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)

    # Convert Area of Interest to 4326 EPSG as obis data is mainly on that Coordinate System. Also simplify the polygon.
    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = aoi_gdf.to_crs(epsg=4326)
    geom = aoi_gdf.geometry.iloc[0]
    geom_s = geom.simplify(0.005, preserve_topology=True)
    wkt_str = wkt_dumps(geom_s, rounding_precision=6)

    print(wkt_str)
    # Set up the occurrence data start and end date:
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    # Restore the column 'aggregation' where we will aggregate the EV values of Nationally Rare Species:
    assessment_grid["aggregation"] = 0

    for specie in species:

        # Intentamos bajarnos los datos, si no hay datos de esa especie pasamos a la siguiente especie:
        try:
            # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
            occ_data = occurrences.search(scientificname=specie, geometry=wkt_str, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()

            # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
            fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
            filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

            # Create geometry of the occurrence data
            geometry = [Point(xy) for xy in zip(filtered_occ_data['decimalLongitude'], filtered_occ_data['decimalLatitude'])]

            # Create the occurrence geodataframe:
            occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)

            # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
            occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

            # Project the occ_gdf into the aoi CRS:
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            # Grid intersecting with occurrence:
            grid_intersect = gpd.sjoin(grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            occ_grid_intersect = grid.loc[grid_intersect.index.unique()].copy()
            assessment_grid.loc[occ_grid_intersect.index, "aggregation"] += 5

        except KeyError:
                pass

    # Average the value with the number of Locally Rare Features
    assessment_grid['aq7'] = assessment_grid["aggregation"]/len(species)

    return assessment_grid

# Assessment Question 10: ecologically significant features indicator:
def ecologically_significant_features_presence(
    aoi: str,
    esf_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    span_years: int
)-> gpd.GeoDataFrame:
    
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
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)

    # Convert Area of Interest to 4326 EPSG as obis data is mainly on that Coordinate System. Also simplify the polygon.
    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = aoi_gdf.to_crs(epsg=4326)
    geom = aoi_gdf.geometry.iloc[0]
    geom_s = geom.simplify(0.005, preserve_topology=True)
    wkt_str = wkt_dumps(geom_s, rounding_precision=6)

    # Set up the occurrence data start and end date:
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    # Restore the column 'aggregation' where we will aggregate the EV values of Nationally Rare Species:
    assessment_grid["aggregation"] = 0

    for specie in esf_species:

        # Intentamos bajarnos los datos, si no hay datos de esa especie pasamos a la siguiente especie:
        try:
            # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
            occ_data = occurrences.search(scientificname=specie, geometry=wkt_str, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()

            # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
            fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
            filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

            # Create geometry of the occurrence data
            geometry = [Point(xy) for xy in zip(filtered_occ_data['decimalLongitude'], filtered_occ_data['decimalLatitude'])]

            # Create the occurrence geodataframe:
            occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)

            # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
            occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

            # Project the occ_gdf into the aoi CRS:
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            # Grid intersecting with occurrence:
            grid_intersect = gpd.sjoin(grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            occ_grid_intersect = grid.loc[grid_intersect.index.unique()].copy()
            assessment_grid.loc[occ_grid_intersect.index, "aggregation"] += 5

        except KeyError:
            pass
    
    # Average the value with the number of Locally Rare Features
    assessment_grid['aq10'] = assessment_grid["aggregation"]/len(esf_species)

    return  assessment_grid

# Assessment Question 12: habitat forming species and biogenic habitats indicator:
def habitat_forming_presence(
    aoi: str,
    hfs_bh_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    span_years: int
)-> gpd.GeoDataFrame:
    
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
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)

    # Convert Area of Interest to 4326 EPSG as obis data is mainly on that Coordinate System. Also simplify the polygon.
    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = aoi_gdf.to_crs(epsg=4326)
    geom = aoi_gdf.geometry.iloc[0]
    geom_s = geom.simplify(0.005, preserve_topology=True)
    wkt_str = wkt_dumps(geom_s, rounding_precision=6)

    print(wkt_str)
    # Set up the occurrence data start and end date:
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    # Restore the column 'aggregation' where we will aggregate the EV values of Nationally Rare Species:
    assessment_grid["aggregation"] = 0

    for specie in hfs_bh_species:

        # Intentamos bajarnos los datos, si no hay datos de esa especie pasamos a la siguiente especie:
        try:
            # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
            occ_data = occurrences.search(scientificname=specie, geometry=wkt_str, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()

            # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
            fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
            filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

            # Create geometry of the occurrence data
            geometry = [Point(xy) for xy in zip(filtered_occ_data['decimalLongitude'], filtered_occ_data['decimalLatitude'])]

            # Create the occurrence geodataframe:
            occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)

            # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
            occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

            # Project the occ_gdf into the aoi CRS:
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            # Grid intersecting with occurrence:
            grid_intersect = gpd.sjoin(grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            occ_grid_intersect = grid.loc[grid_intersect.index.unique()].copy()
            assessment_grid.loc[occ_grid_intersect.index, "aggregation"] += 5

        except KeyError:
            pass
    
    # Average the value with the number of Locally Rare Features
    assessment_grid['aq12'] = assessment_grid["aggregation"]/len(hfs_bh_species)

    return  assessment_grid

# Assessment Question 14: mutualistic/symbiotic species indicator:
def mutualistic_symbiotic_presence(
    aoi: str,
    mss_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    span_years: int
)-> gpd.GeoDataFrame:
    
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
        metric_crs = aoi_gdf.crs
    else:
        metric_crs = best_utm_crs(aoi)

    # Convert Area of Interest to 4326 EPSG as obis data is mainly on that Coordinate System. Also simplify the polygon.
    from shapely.wkt import dumps as wkt_dumps
    aoi_gdf = aoi_gdf.to_crs(epsg=4326)
    geom = aoi_gdf.geometry.iloc[0]
    geom_s = geom.simplify(0.005, preserve_topology=True)
    wkt_str = wkt_dumps(geom_s, rounding_precision=6)

    print(wkt_str)
    # Set up the occurrence data start and end date:
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    # Restore the column 'aggregation' where we will aggregate the EV values of Nationally Rare Species:
    assessment_grid["aggregation"] = 0

    for specie in mss_species:

        # Intentamos bajarnos los datos, si no hay datos de esa especie pasamos a la siguiente especie:
        try:
            # Download the species occurrence data from pyobis (we will use the occurrence data of the last 10 years):
            occ_data = occurrences.search(scientificname=specie, geometry=wkt_str, startdate=start_date.strftime("%Y-%m-%d"), enddate=end_date.strftime("%Y-%m-%d")).execute()

            # Drop duplicates and keep just the fields 'scientificName', 'geodeicDatum' (Coordinate System), 'datasetID', Latitude and Longitude
            fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
            filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

            # Create geometry of the occurrence data
            geometry = [Point(xy) for xy in zip(filtered_occ_data['decimalLongitude'], filtered_occ_data['decimalLatitude'])]

            # Create the occurrence geodataframe:
            occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)

            # Establish the Coordinate System to EPSG:4326 (it has to be equal to geodeticDatum):
            occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)

            # Project the occ_gdf into the aoi CRS:
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            # Grid intersecting with occurrence:
            grid_intersect = gpd.sjoin(grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            occ_grid_intersect = grid.loc[grid_intersect.index.unique()].copy()
            assessment_grid.loc[occ_grid_intersect.index, "aggregation"] += 5

        except KeyError:
            pass
    
    # Average the value with the number of Locally Rare Features
    assessment_grid['aq14'] = assessment_grid["aggregation"]/len(mss_species)

    return  assessment_grid


# aq7_grid_test = mutualistic_symbiotic_presence(aoi=aoi, mss_species= ["Spartina", "Delphinus delphis", "Halimione", "Diplodus"], assessment_grid=grid, span_years=30)

# aq7_grid_test.to_parquet(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\eez_grisd_test.parquet")

