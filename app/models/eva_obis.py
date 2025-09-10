from __future__ import annotations

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Union, Dict

import numpy as np
import geopandas as gpd
from pyproj import CRS
from shapely.geometry import box, Point
from shapely.wkt import dumps as wkt_dumps
from pyobis.occurrences import occurrences


# ================================================================
# Utils
# ================================================================

class AQUtils:
    @staticmethod
    def load_aoi(aoi: Union[str, gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        if isinstance(aoi, gpd.GeoDataFrame):
            return aoi
        if not aoi.endswith((".json", ".geojson", ".parquet")):
            raise ValueError("Unsupported AOI file format (.json, .geojson, .parquet).")
        return gpd.read_parquet(aoi) if aoi.endswith(".parquet") else gpd.read_file(aoi)

    @staticmethod
    def ensure_metric_crs(gdf: gpd.GeoDataFrame, aoi: Union[str, gpd.GeoDataFrame]) -> Tuple[gpd.GeoDataFrame, CRS]:
        if gdf.crs and gdf.crs.is_projected:
            return gdf, gdf.crs
        metric_crs = best_utm_crs(aoi)
        return gdf.to_crs(metric_crs), metric_crs

    @staticmethod
    def get_obis_occurrences(specie: str, wkt_geom: str, start_date: str, end_date: str) -> gpd.GeoDataFrame:
        """
        Igual que en tu código original (sin “limpieza extra”):
        - Descarga de OBIS
        - Drop duplicates por lat/lon
        - Selección de columnas esperadas
        - Construcción de puntos y CRS EPSG:4326
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
    """Elige UTM por el centroide del AOI en lat/lon."""
    aoi_gdf = AQUtils.load_aoi(aoi)
    g_ll = aoi_gdf.to_crs(4326) if (aoi_gdf.crs and aoi_gdf.crs.to_epsg() != 4326) else aoi_gdf
    c = g_ll.unary_union.centroid
    lon, lat = c.x, c.y
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)


def create_grid(aoi: Union[str, gpd.GeoDataFrame], grid_size: int = 1000) -> gpd.GeoDataFrame:
    """Crea un grid cuadrado que cubre el AOI y filtra por intersección con el AOI."""
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


def ensure_grid_crs(grid: gpd.GeoDataFrame, target_crs: CRS) -> gpd.GeoDataFrame:
    """Asegura que el grid está en el CRS objetivo (si no, reproyecta)."""
    if grid.crs is None:
        raise ValueError("assessment_grid sin CRS.")
    if grid.crs != target_crs:
        return grid.to_crs(target_crs)
    return grid


def safe_sjoin_polys_points(polys: gpd.GeoDataFrame, points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Inner sjoin con predicate='intersects' y manejo de índices únicos."""
    hits = gpd.sjoin(polys, points[["geometry"]], how="inner", predicate="intersects")
    return polys.loc[hits.index.unique()].copy()


def wkt_from_first_geom(aoi_gdf_4326: gpd.GeoDataFrame, simplify_tol: float = 0.005) -> str:
    """Replica exactamente tu forma original de construir el WKT: primera geometría + simplify."""
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
    """AQ1: presencia de Localmente Raras (LRF), replicando el cálculo original."""
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
    """AQ5: presencia de Nacionalmente Raras (NRF), replicando tu cálculo original con EEZ por bbox."""
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

    eez_grid = create_grid(eez_gdf_4326, grid_size=grid_size).to_crs(metric_crs)
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
    span_years: int
) -> gpd.GeoDataFrame:
    """
    AQ7: número de features (presencia/ausencia).
    Se restaura el patrón original: WKT de la primera geometría + try/except KeyError
    alrededor de la descarga y el procesado por especie.
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

    assessment_grid["aq7"] = (assessment_grid["aggregation"] / len(species)) if species else 0
    return assessment_grid


def ecologically_significant_features_presence(
    aoi: str,
    esf_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int
) -> gpd.GeoDataFrame:
    out = feature_number_presence(aoi, esf_species, assessment_grid, min_grid_per, span_years)
    out["aq10"] = out.pop("aq7")
    return out


def habitat_forming_presence(
    aoi: str,
    hfs_bh_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int
) -> gpd.GeoDataFrame:
    out = feature_number_presence(aoi, hfs_bh_species, assessment_grid, min_grid_per, span_years)
    out["aq12"] = out.pop("aq7")
    return out


def mutualistic_symbiotic_presence(
    aoi: str,
    mss_species: List[str],
    assessment_grid: gpd.GeoDataFrame,
    min_grid_per: int,
    span_years: int
) -> gpd.GeoDataFrame:
    out = feature_number_presence(aoi, mss_species, assessment_grid, min_grid_per, span_years)
    out["aq14"] = out.pop("aq7")
    return out


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


# Testing the optimized functions:
aoi_path = r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\cantabria.geojson"
ass_grid_size = 1000
min_grid_per = 1
grid = create_grid(aoi_path, grid_size=ass_grid_size)
general_species = ["Spartina", "Halimione", "Diplodus", "Delphinus delphis", "Sparus", "Sardina"]

params = {
    "aq1": {
        "species": general_species,
        #"min_grid_per": 1,
        "cut_lrf": 99
    },
    "aq5": {
        "species": general_species,
        "country_name": "Spain",
        "grid_size": 10000,
        #"min_grid_per": 1,
        "cut_nrf": 99
    },
    "aq7": {
        "species": general_species
    },
    "aq10": {
        "esf_species": ["Spartina", "Halimione", "Diplodus", "Sardina"]
    },
    "aq12": {
        "hfs_bh_species": ["Spartina", "Halimione"]
    },
    "aq14": {
        "mss_species": ["Diplodus"]
    }
}

result = run_selected_assessments(
    aoi_path=aoi_path,
    grid=grid,
    min_grid_per = min_grid_per,
    span_years=30,
    params=params
)

result.to_parquet(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA\optimized_test.parquet")