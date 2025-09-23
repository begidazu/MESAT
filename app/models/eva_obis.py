from __future__ import annotations

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Union, Dict

import os
import numpy as np
import geopandas as gpd
import h3
from pyproj import CRS
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps
from pyobis.occurrences import occurrences


# ================================================================
# Utils
# ================================================================

class AQUtils:
    @staticmethod
    def load_aoi(aoi: Union[str, gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """
        Reads the area of interest file and returns a gpd.GeoDataFrame. Supported input formats: .json, .geojson, .parquet.
        """
        if isinstance(aoi, gpd.GeoDataFrame):
            return aoi
        if not aoi.endswith((".json", ".geojson", ".parquet")):
            raise ValueError("Unsupported AOI file format (.json, .geojson, .parquet).")
        return gpd.read_parquet(aoi) if aoi.endswith(".parquet") else gpd.read_file(aoi)

    @staticmethod
    def ensure_metric_crs(gdf: gpd.GeoDataFrame, aoi: Union[str, gpd.GeoDataFrame]) -> Tuple[gpd.GeoDataFrame, CRS]:
        """
        Ensures a gpd.GeoDataFrame coordinate system is projected reproyecting it into the best UTM coordinate system in case it is in a non-proyected coordinate system. 
        """
        if gdf.crs and gdf.crs.is_projected:
            return gdf, gdf.crs
        metric_crs = best_utm_crs(aoi)
        return gdf.to_crs(metric_crs), metric_crs

    @staticmethod
    def get_obis_occurrences(specie: str, wkt_geom: str, start_date: str, end_date: str) -> gpd.GeoDataFrame:
        """
        Downloads species occurrence data in the area of interest during the selected timeframe in the EPSG:4326 coordinate system.

        Params:
            specie: specie name
            wkt_geom:  a WKT string of the area of interest where we want to download the occurrence data
            start_date: start date in %Y-%m-%d format
            end_date:  end date in %Y-%m-%d format
        
        Returns:
        A gpd.GeoDataFrame with the occurrence points of the specie. From the points with same lat/long the function keeps the first point. 
        """
        occ_data = occurrences.search(
            scientificname=specie,
            geometry=wkt_geom,
            startdate=start_date,
            enddate=end_date
        ).execute()

        fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
        filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

        geometry = [Point(xy) for xy in zip(filtered_occ_data["decimalLongitude"], filtered_occ_data["decimalLatitude"])]
        occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)
        occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)
        return occ_gdf


def best_utm_crs(aoi: Union[str, gpd.GeoDataFrame]) -> CRS:
    """
    Choses the best UTM coordinate system for the area of interest based on the centroid of the AOI
    """
    aoi_gdf = AQUtils.load_aoi(aoi)
    g_ll = aoi_gdf.to_crs(4326) if (aoi_gdf.crs and aoi_gdf.crs.to_epsg() != 4326) else aoi_gdf
    c = g_ll.unary_union.centroid
    lon, lat = c.x, c.y
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)


def create_quadrat_grid(aoi: Union[str, gpd.GeoDataFrame], grid_size: int = 1000) -> gpd.GeoDataFrame:
    """
    Creates a grid that covers the area of interest and filters the grid to keep the grids that intersect with the AOI
    """
    aoi_gdf = AQUtils.load_aoi(aoi)
    gdf_m, metric_crs = AQUtils.ensure_metric_crs(aoi_gdf, aoi)

    min_x, min_y, max_x, max_y = gdf_m.total_bounds
    grid_cells = [
        box(x0, y0, x0 + grid_size, y0 + grid_size)
        for x0 in np.arange(min_x, max_x, grid_size)
        for y0 in np.arange(min_y, max_y, grid_size)
    ]
    cells = gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs=metric_crs)
    return cells[cells.intersects(gdf_m.unary_union)].copy()

def create_h3_grid(aoi: str, h3_resolution: int) -> gpd.GeoDataFrame:
    """
    Generates a GeoDataFrame of H3 cells that intersect with the AOI. Input AOI path file accepted formats are .json, .geojson and .parquet.
    """
    resolution = int(h3_resolution)
    if not (0 <= resolution <= 15):
        raise ValueError("resolution debe estar entre 0 y 15 (entero).")

    aoi = AQUtils.load_aoi(aoi)
    aoi = aoi.to_crs(4326) if aoi.crs else aoi.set_crs(4326)

    geoms = aoi.geometry.explode(index_parts=False)
    if geoms.empty:
        return gpd.GeoDataFrame(columns=["h3", "geometry"], crs="EPSG:4326")

    union_geom = geoms.unary_union
    if union_geom.is_empty:
        return gpd.GeoDataFrame(columns=["h3", "geometry"], crs="EPSG:4326")

    # Get polygons to generate H3 cells
    polygons = [poly for geom in geoms if not geom.is_empty and geom.geom_type in ("Polygon", "MultiPolygon") for poly in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom])]

    cells = set()
    for poly in polygons:

        if hasattr(poly, "has_z") and poly.has_z:
            poly = Polygon(
                [(x, y) for x, y, *_ in np.asarray(poly.exterior.coords)],
                holes=[[(x, y) for x, y, *_ in np.asarray(r.coords)] for r in poly.interiors]
            )
        cells.update(h3.geo_to_cells(poly, res=resolution))

    if not cells:
        return gpd.GeoDataFrame(columns=["h3", "geometry"], crs="EPSG:4326")

    all_cells = {neighbor for cell in cells for neighbor in h3.grid_disk(cell, k=5)}

    hex_geoms = [(cid, Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cid)])) for cid in all_cells]

    hex_df = gpd.GeoDataFrame(hex_geoms, columns=["h3", "geometry"], crs="EPSG:4326")

    return hex_df[hex_df.intersects(union_geom)].reset_index(drop=True)


def ensure_grid_crs(grid: gpd.GeoDataFrame, target_crs: CRS) -> gpd.GeoDataFrame:
    """
    Ensures the grid is with the objective CRS
    """
    if grid.crs is None:
        raise ValueError("assessment_grid sin CRS.")
    if grid.crs != target_crs:
        return grid.to_crs(target_crs)
    return grid


def wkt_from_first_geom(aoi_gdf_4326: gpd.GeoDataFrame, simplify_tol: float = 0.005) -> str:
    """
    Converts the area of interest geometries into a WKT string that will be used to download OBIS data
    """
    geom = aoi_gdf_4326.geometry.iloc[0]
    geom_s = geom.simplify(simplify_tol, preserve_topology=True)
    return wkt_dumps(geom_s, rounding_precision=6)


# ================================================================
# AQs
# ================================================================

def locally_rare_features_presence(
    aoi: str,
    species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    cut_lrf: int,
    span_years: int
) -> gpd.GeoDataFrame:
    """
    AQ1: presence of Locally Rare Features (LRF). Returns 'aq1' column in the assessment grid with an indicator of LRF presence/absence based on the selected parameters.

    The function downloads the OBIS data for all the included species in the AOI and with the selected timespan (presence to presence - span_years), check if the occurrence data covers a minimum threshold of the assessment grid: if it has a minimum coverage the specie is included in computation, if not the function passes to the next specie. Then, the LRF are added into a list where the species with lower grid coverage than cut_lrf are included. Finally, it computes an indicator (0 to 5, very low yo very high) with a score of LRF presence/absence based on the LRF species list. This score is computed as the average of presence/absence scores where a value of 5 is given to a cell when a LRF is present and a 0 when it is absent, repeating the process for all species and averaging the final score with the lenght of the LRF species list.
    
    Params:
        aoi: area of interest path
        species: list of species names to include in the assessment
        assessment_grid: gpd.GeoDataFrame where the assessement is conducted
        min_grid_per: minimum gri coverage needed to include the species in the assessment
        cut_lrf: cutoff to consider a specie as locally rare feature or not
        span_years: time span of the downloaded occurence data from the present (e.g. span_years = 10 will download occurrence data from present to present-10 years).

    Returns:
    Returns a gpd.GeoDataFrame with a 'aq1' column with the score (0 to 5, worse to best) of LRF presence/absence.
    """
    aoi_gdf_4326 = AQUtils.load_aoi(aoi).to_crs(4326)
    _, metric_crs = AQUtils.ensure_metric_crs(aoi_gdf_4326, aoi)
    assessment_grid = ensure_grid_crs(assessment_grid, metric_crs)

    wkt_str = wkt_from_first_geom(aoi_gdf_4326)
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    assessment_grid["aggregation"] = 0
    lrs_array = []

    for specie in species:
        try:
            occ_gdf = AQUtils.get_obis_occurrences(
                specie, wkt_str, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
        except Exception:
            continue

        if occ_gdf.empty:
            continue

        occ_gdf_proj = occ_gdf.to_crs(metric_crs)

        intersect = gpd.sjoin(assessment_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
        occ_grid = assessment_grid.loc[intersect.index.unique()].copy()

        percent = (len(occ_grid) / len(assessment_grid)) * 100 if len(assessment_grid) else 0.0
        if percent < min_grid_per:
            continue
        if percent < cut_lrf:
            lrs_array.append(specie)
            assessment_grid.loc[occ_grid.index, "aggregation"] += 5

    assessment_grid["aq1"] = assessment_grid["aggregation"] / len(lrs_array) if lrs_array else 0
    return assessment_grid


def nationally_rare_feature_presence(
    aoi: str,
    species: List[str],
    country_name: str,
    grid_size: int,
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    cut_nrf: int,
    span_years: int
) -> gpd.GeoDataFrame:
    """
    AQ5: presence of Nationally Rare Features (LRF). Returns 'aq5' column in the assessment grid with an indicator of NRF presence/absence based on the selected parameters.

    The function downloads the OBIS data for all the included species in the Exclusive Economic Zone of the selected country and with the selected timespan (presence to presence - span_years), checks if the occurrence data covers a minimum threshold of the assessment grid: if it has a minimum coverage the specie is included in computation, if not the function passes to the next specie. Then, a grid on the EEZ is created with the grid_size selected by the user. The NRF are added into a list where the species with lower grid coverage (on the EEZ grid) than cut_nrf are included. Finally, it computes an indicator in the assessment grid (0 to 5, very low yo very high) with a score of NRF presence/absence based on the NRF species list. This score is computed as the average of presence/absence scores where a value of 5 is given to a cell when a NRF is present and a 0 when it is absent, repeating the process for all species and averaging the final score with the lenght of the NRF species list.
    
    Params:
        aoi: area of interest path
        species: list of species names to include in the assessment
        country_name: name of the country where the AOI is located
        grid_size: size of the grid in meters to be used in the EEZ of the country
        assessment_grid: gpd.GeoDataFrame where the assessement is conducted
        min_grid_per: minimum gri coverage needed to include the species in the assessment
        cut_lrf: cutoff to consider a specie as locally rare feature or not
        span_years: time span of the downloaded occurence data from the present (e.g. span_years = 10 will download occurrence data from present to present-10 years).

    Returns:
    Returns a gpd.GeoDataFrame with a 'aq5' column with the score (0 to 5, worse to best) of NRF presence/absence.
    """
    eez_path = "./results/EVA/world_eez.parquet"
    eez_file = gpd.read_parquet(eez_path)
    eez_gdf_4326 = eez_file[eez_file.SOVEREIGN1 == country_name].to_crs(4326)
    if eez_gdf_4326.empty:
        raise ValueError(f"No se encontró EEZ para '{country_name}' en {eez_path}")

    minx, miny, maxx, maxy = eez_gdf_4326.total_bounds
    bbox = box(minx, miny, maxx, maxy)
    wkt_str = wkt_dumps(bbox, rounding_precision=6)

    aoi_gdf_4326 = AQUtils.load_aoi(aoi).to_crs(4326)
    _, metric_crs = AQUtils.ensure_metric_crs(aoi_gdf_4326, aoi)

    eez_grid = create_quadrat_grid(eez_gdf_4326, grid_size=grid_size).to_crs(metric_crs)
    assessment_grid = ensure_grid_crs(assessment_grid, metric_crs)

    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    assessment_grid["aggregation"] = 0
    nrs_array = []

    for specie in species:
        try:
            occ_gdf = AQUtils.get_obis_occurrences(
                specie, wkt_str, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
        except Exception:
            continue

        if occ_gdf.empty:
            continue
        
        occ_gdf_proj = occ_gdf.to_crs(metric_crs)

        # porcentaje sobre grid de la EEZ
        eez_intersect = gpd.sjoin(eez_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
        eez_occ_grid = eez_grid.loc[eez_intersect.index.unique()].copy()
        percent = (len(eez_occ_grid) / len(eez_grid)) * 100 if len(eez_grid) else 0.0

        if percent < min_grid_per:
            continue
        if percent < cut_nrf:
            nrs_array.append(specie)
            aoi_intersect = gpd.sjoin(assessment_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            aoi_occ_grid = assessment_grid.loc[aoi_intersect.index.unique()].copy()
            assessment_grid.loc[aoi_occ_grid.index, "aggregation"] += 5

    assessment_grid["aq5"] = assessment_grid["aggregation"] / len(nrs_array) if nrs_array else 0
    return assessment_grid


def feature_number_presence(
    aoi: str,
    species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int,
    target_col: str = "aq7"
) -> gpd.GeoDataFrame:
    """
    AQ7, AQ10, AQ12 and/or AQ14: presence of Feature Number (AQ7), Ecologically Significant Features (AQ10), Habitat Forming Species/Biogenic Habitats (AQ12) and/ or Mutualistic-Symbiotic Species (AQ14). Returns 'aq7', 'aq10', 'aq12' and/or 'aq14' column in the assessment grid with an indicator of FN, ESF, HFS/BH and/or MSS presence/absence based on the selected parameters.

    Same logic of the AQ1 function with the lists of FN, ESF, HFS/BH and/or MSS.
    
    Params:
        aoi: area of interest path
        species: list of species names to include in the assessment
        assessment_grid: gpd.GeoDataFrame where the assessement is conducted
        min_grid_per: minimum gri coverage needed to include the species in the assessment
        span_years: time span of the downloaded occurence data from the present (e.g. span_years = 10 will download occurrence data from present to present-10 years).

    Returns:
    Returns a gpd.GeoDataFrame with 'aq7', 'aq10', 'aq12' and/or 'aq14' column with the score (0 to 5, worse to best) of FN, ESF, HFS/BH and/or MSS presence/absence.
    """
    aoi_gdf_4326 = AQUtils.load_aoi(aoi).to_crs(4326)
    _, metric_crs = AQUtils.ensure_metric_crs(aoi_gdf_4326, aoi)
    assessment_grid = ensure_grid_crs(assessment_grid, metric_crs)

    # Igual que tu original: primera geometría + simplify
    wkt_str = wkt_from_first_geom(aoi_gdf_4326)

    end_date = datetime.now()
    start_date = end_date - relativedelta(years=span_years)

    assessment_grid["aggregation"] = 0

    for specie in species:
        try:
            occ_gdf = AQUtils.get_obis_occurrences(
                specie, wkt_str, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )
            if occ_gdf is None or occ_gdf.empty:
                continue
            
            #occ_gdf.to_parquet(os.path.join (r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria", f"{specie.replace(' ', '_')}.parquet"))
            occ_gdf_proj = occ_gdf.to_crs(metric_crs)

            grid_intersect = gpd.sjoin(assessment_grid, occ_gdf_proj[["geometry"]], how="inner", predicate="intersects")
            occ_grid_intersect = assessment_grid.loc[grid_intersect.index.unique()].copy()

            # percentage of grid ocurrence:
            percent = (len(occ_grid_intersect) / len(assessment_grid)) * 100 if len(assessment_grid) else 0.0
            if percent < min_grid_per:
                continue

            assessment_grid.loc[occ_grid_intersect.index, "aggregation"] += 5

        except KeyError:
            # Tal como en tu código original: si faltan columnas, se ignora esa especie
            continue
        except Exception:
            # Evita que una especie problemática rompa toda la AQ
            continue

    assessment_grid[target_col] = (assessment_grid["aggregation"] / len(species)) if species else 0
    return assessment_grid


def ecologically_significant_features_presence(
    aoi: str,
    esf_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int
) -> gpd.GeoDataFrame:
    return feature_number_presence(aoi, esf_species, assessment_grid, min_grid_per, span_years, target_col="aq10")


def habitat_forming_presence(
    aoi: str,
    hfs_bh_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int
) -> gpd.GeoDataFrame:
    return feature_number_presence(aoi, hfs_bh_species, assessment_grid, min_grid_per, span_years, target_col="aq12")


def mutualistic_symbiotic_presence(
    aoi: str,
    mss_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int
) -> gpd.GeoDataFrame:
    return feature_number_presence(aoi, mss_species, assessment_grid, min_grid_per, span_years, target_col="aq14")


# ================================================================
# Dispatcher (ejecutar 1..n AQs)
# ================================================================

def run_selected_assessments(
    aoi_path: str,
    grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int,
    params: Dict[str, Dict]
) -> gpd.GeoDataFrame:
    function_map = {
        "aq1": locally_rare_features_presence,
        "aq5": nationally_rare_feature_presence,
        "aq7": feature_number_presence,
        "aq10": ecologically_significant_features_presence,
        "aq12": habitat_forming_presence,
        "aq14": mutualistic_symbiotic_presence,
    }

    results = grid.copy()
    for aq_key, func_args in params.items():
        func = function_map.get(aq_key)
        if not func:
            print(f"AVISO: AQ desconocido '{aq_key}', se omite.")
            continue
        print(f"Running {aq_key}...")
        results = func(
            aoi=aoi_path,
            assessment_grid=results,
            min_grid_per=min_grid_per, 
            span_years=span_years,
            **func_args
        )
    return results


# # Testing the optimized functions:
# aoi_path = r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.parquet"
# ass_grid_size = 1000
# min_grid_per = 0
# #grid = create_quadrat_grid(aoi_path, grid_size=ass_grid_size)
# grid = create_h3_grid(aoi_path, 9)

# # List of LRF, RRF, NRF, ESF, HFS/BH & MSS for each ecosystem component:
# lrf_species = []
# rrf_species = ["Zostera noltii"]
# nrf_species = ["Zostera noltii"]
# esf_species = ["Codium tomentosum", "Dictyota dichotoma", "Plocamium cartilagineum"]
# hfs_bh_species = ["Corallina officinalis", "Cystoseira baccata", "Gelidium corneum", "Halidrys siliquosa", "Halopteris scoparia", "Laminaria ochroleuca", "Mesophyllum", "Saccorhiza polyschides"]
# mss_species = []
# all_species = lrf_species + rrf_species + nrf_species + esf_species + hfs_bh_species + mss_species
# params = {
#     # "aq1": {
#     #     "species": lrf_species,
#     #     #"min_grid_per": 1,
#     #     "cut_lrf": 99
#     # },
#     # "aq5": {
#     #     "species": nrf_species,
#     #     "country_name": "Spain",
#     #     "grid_size": 10000,
#     #     #"min_grid_per": 1,
#     #     "cut_nrf": 99
#     # },
#     "aq7": {
#         "species": all_species
#     },
#     "aq10": {
#         "esf_species": esf_species
#     },
#     "aq12": {
#         "hfs_bh_species": hfs_bh_species
#     }
#     # "aq14": {
#     #     "mss_species": mss_species
#     # }
# }

# result = run_selected_assessments(
#     aoi_path=aoi_path,
#     grid=grid,
#     min_grid_per = min_grid_per,
#     span_years=15,
#     params=params
# )

# result.to_parquet(os.path.join (r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria", "subtidal_macroalgae.parquet"))

