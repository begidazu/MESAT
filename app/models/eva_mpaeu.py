from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import math, os, pyproj
import numpy as np
import geopandas as gpd
import pandas as pd
import s3fs
import pyarrow as pa
import pyarrow.dataset as ds
import rasterio as rio
from shapely.geometry import box
from shapely import intersects
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window
from pathlib import PurePosixPath
from eva_obis import create_h3_grid, create_quadrat_grid

from scipy.spatial import cKDTree

# PROJ del venv (pyproj)
os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()

# Functions to construct paths to the S3 public bucket of MPAEU project:
class MPAEU_AWS_Utils:
    @staticmethod
    def get_env_kwargs():
        """Envrionment for S3 public bucket configuration"""
        return {
            "AWS_NO_SIGN_REQUEST": "YES",                 # If the bucket is public set to YES
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",  # Avoids extra HEAD requests
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.json",
        }
    
    @staticmethod
    def mpaeu_tif_vsis3(taxonid: int, model: str, method: str, scenario: str) -> str:
        """ Constructs the path to retrieve the SDM prediction COG"""
        base = PurePosixPath("mpaeu-dist/results/species")
        tif_name = f"taxonid={taxonid}_model={model}_method={method}_scen={scenario}.tif"
        key = base / f"taxonid={taxonid}" / f"model={model}" / "predictions" / tif_name
        return f"/vsis3/{key}"
    
    @staticmethod
    def mpaeu_tif_mask_vsis3(taxonid: int, model: str, mask_model: str) -> str:
        """ Constructs the path to retireve the SDM mask"""
        base = PurePosixPath("mpaeu-dist/results/species")
        tif_name = f"taxonid={taxonid}_model={mask_model}.tif"
        key = base / f"taxonid={taxonid}" / f"model={model}" / "predictions" / tif_name
        return f"/vsis3/{key}"
    
    @staticmethod
    def mpaeu_presence_threshold_p10(taxonid: int, model: str = "mpaeu") -> int:
        """ Obtains the p10 threshold from the parquet file in the S3 bucket. More info in : https://iobis.github.io/mpaeu_docs/datause.html"""
        path = (f"mpaeu-dist/results/species/taxonid={taxonid}/model={model}/metrics/"
                f"taxonid={taxonid}_model={model}_what=thresholds.parquet") 
        fs = s3fs.S3FileSystem(anon=True)

        schema = pa.schema([("model", pa.string()), ("p10", pa.float64())])

        dset = ds.dataset(path, filesystem=fs, format="parquet", schema=schema)
        table = dset.to_table(columns=["model", "p10"])
        df = table.to_pandas()
        s = df.loc[df["model"] == "ensemble", "p10"]
        return int(round(s.iloc[0] * 100)) if not s.empty else None
    
    @staticmethod
    def fit_regions_prediction(taxonid: int, model: str, method: str, scenario: str, presence_threshold: float = 50):
        """ Fits the SDM predictions to the selected threshold and returns the masked prediction, the masked presence/absence, extent of the prediction and SDM coordinate system"""
        mask_model = "mpaeu_mask_cog"
        predic_path = MPAEU_AWS_Utils.mpaeu_tif_vsis3(taxonid, model, method, scenario)
        mask_path = MPAEU_AWS_Utils.mpaeu_tif_mask_vsis3(taxonid, model, mask_model)
        presence_threshold = MPAEU_AWS_Utils.mpaeu_presence_threshold_p10(taxonid, model)
        print(f"[{taxonid}] presence_threshold (p10) = {presence_threshold}")
        with rio.Env(**MPAEU_AWS_Utils.get_env_kwargs()):
            with rio.open(predic_path) as src, rio.open(mask_path) as mask:
                prediction = src.read(1, masked=True)
                prediction_mask = mask.read(3, masked=True) # band 3. See for further mask options: https://iobis.github.io/mpaeu_docs/datause.html
                masked_prediction = np.where(prediction_mask==1, prediction, np.nan)
                masked_presence = np.where(masked_prediction>=presence_threshold, 1, np.where((masked_prediction<presence_threshold) & (masked_prediction>=0), 0, np.nan))
                left, bottom, right, top = src.bounds
                extent = (left, bottom, right, top) 
                return masked_prediction, masked_presence, extent, src.crs
        

@dataclass
class EVA_MPAEU:
    model: str = "mpaeu"
    method: str = "ensemble"
    scenario: str = "current_cog"
    presence_threshold: float = 50.0
    all_touched: bool = True         
    pad_factor: float = 0.5          # half pixel margin in each cell

    # ------------- Static helpers -------------

    @staticmethod
    def _round_clip_window(win: Window, h: int, w: int) -> Optional[Tuple[int, int, int, int]]:
        """ Rounds and clips the window to image bounds. """
        r0 = int(math.floor(win.row_off)); c0 = int(math.floor(win.col_off))
        r1 = r0 + int(math.ceil(win.height)); c1 = c0 + int(math.ceil(win.width))
        r0 = max(0, r0); c0 = max(0, c0); r1 = min(h, r1); c1 = min(w, c1)
        if r1 <= r0 or c1 <= c0:
            return None
        return r0, r1, c0, c1

    @staticmethod
    def _transform_from_extent(extent: Tuple[float, float, float, float], width: int, height: int):
        xmin, ymin, xmax, ymax = extent
        return rio.transform.from_bounds(xmin, ymin, xmax, ymax, width=width, height=height)

    # ------------- Functions to match presence cells to assessment -------------

    def _present_indices(
        self,
        grid: gpd.GeoDataFrame,
        presence: np.ndarray,                # array 2D con {1,0,NaN}
        extent: Tuple[float, float, float, float],  # (xmin, ymin, xmax, ymax)
        raster_crs,                          # CRS del raster (rasterio.crs.CRS)
    ) -> List[int]:
        
        """ Returns the indices of the assessment grid with presence of the target species. Presence-absence is not interpolated to grids with NoData"""

        if grid.crs is None:
            raise ValueError("assessment_grid sin CRS.")
        grid_r = grid.to_crs(raster_crs)

        if not np.isfinite(presence).any() or (np.nanmax(presence) < 0.5):
            return []

        xmin, ymin, xmax, ymax = extent
        transform = self._transform_from_extent(extent, width=presence.shape[1], height=presence.shape[0])
        raster_bbox = box(xmin, ymin, xmax, ymax)

        # si no hay solape con el AOI
        if not raster_bbox.intersects(box(*grid_r.total_bounds)):
            return []

        H, W = presence.shape
        px, py = abs(transform.a), abs(transform.e)          # tamaño de píxel en unidades del CRS
        pad_x, pad_y = self.pad_factor * px, self.pad_factor * py

        present_idx: List[int] = []

        for idx, geom in zip(grid_r.index, grid_r.geometry):
            if geom.is_empty or not geom.intersects(raster_bbox):
                continue

            gxmin, gymin, gxmax, gymax = geom.bounds
            win = from_bounds(gxmin - pad_x, gymin - pad_y, gxmax + pad_x, gymax + pad_y, transform=transform)
            rc = self._round_clip_window(win, H, W)
            if rc is None:
                continue
            r0, r1, c0, c1 = rc
            tile = presence[r0:r1, c0:c1]

            # máscara geométrica real (no solo bbox)
            win_transform = rio.windows.transform(Window(c0, r0, c1 - c0, r1 - r0), transform)
            geom_mask = geometry_mask(
                [geom], out_shape=tile.shape, transform=win_transform, invert=True, all_touched=self.all_touched
            )

            valid = np.isfinite(tile)
            pres = (tile >= 0.5) & valid & geom_mask

            if pres.any():
                present_idx.append(idx)

        return present_idx

    def _present_indices_with_nearest_optimized(
        self,
        grid: gpd.GeoDataFrame,
        presence: np.ndarray,
        extent: Tuple[float, float, float, float],
        raster_crs,
        coastline_parquet_path: str = "./results/EVA/coastline_20km_buffer_4326.parquet",
    ) -> List[int]:
        
        """ Returns the indices of the assessment grid with presence of the target species. Presence-absence is interpolated to grids with NoData"""

        if grid.crs is None:
            raise ValueError("assessment_grid sin CRS.")

        H, W = presence.shape
        transform = self._transform_from_extent(extent, width=W, height=H)
        raster_bbox = box(*extent)

        # Transform the grid to the SDM coordinate system
        grid_r = grid.to_crs(raster_crs)
        idx_pos_map = list(grid_r.index)
        y = np.full(len(idx_pos_map), np.nan, dtype=float)

        px, py = abs(transform.a), abs(transform.e)
        pad_x, pad_y = self.pad_factor * px, self.pad_factor * py

        grid_r_bounds = grid_r.geometry.bounds.values
        grid_r_geoms = grid_r.geometry.values
        grid_r_centroids = np.vstack([geom.centroid.coords[0] for geom in grid_r_geoms])

        # --- Cell classification ---
        for pos, (geom, bounds) in enumerate(zip(grid_r_geoms, grid_r_bounds)):
            if geom.is_empty or not geom.intersects(raster_bbox):
                continue

            gxmin, gymin, gxmax, gymax = bounds
            win = from_bounds(gxmin - pad_x, gymin - pad_y, gxmax + pad_x, gymax + pad_y, transform=transform)
            rc = self._round_clip_window(win, H, W)
            if rc is None:
                continue

            r0, r1, c0, c1 = rc
            tile = presence[r0:r1, c0:c1]

            win_transform = rio.windows.transform(Window(c0, r0, c1 - c0, r1 - r0), transform)
            geom_mask = geometry_mask(
                [geom],
                out_shape=tile.shape,
                transform=win_transform,
                invert=True,
                all_touched=self.all_touched
            )

            valid = np.isfinite(tile) & geom_mask
            if not valid.any():
                y[pos] = np.nan
            else:
                y[pos] = 1.0 if (tile[valid] == 1).any() else 0.0

        # --- Interpolation using the nearest neighbour (only in the cells close to the coast, where NoData is due to data lack insetad of SDM mask) ---
        if np.isnan(y).any():
            coast = gpd.read_parquet(coastline_parquet_path)
            coast = coast.set_crs(4326) if coast.crs is None else coast
            coast = coast.to_crs(grid.crs)

            grid_orig = grid  
            intersects_mask = grid_orig.intersects(coast.unary_union).to_numpy()

            nan_mask = np.isnan(y)
            nan_idxs = np.where(nan_mask)[0]

            # Ensure all arrays have lenght equal to y
            assert len(intersects_mask) == len(y), f"intersects_mask: {len(intersects_mask)}, y: {len(y)}"

            # Check NaN cells that intersect with the coastline buffer
            nan_and_inside = nan_idxs[intersects_mask[nan_idxs]]

            if nan_and_inside.size > 0:
                known_mask = np.isfinite(y)
                if known_mask.any():
                    # Use centroids in the same CRS of the SDM
                    pts_known = grid_r_centroids[known_mask]
                    vals_known = y[known_mask].astype(float)

                    tree = cKDTree(pts_known)
                    query_pts = grid_r_centroids[nan_and_inside]
                    _, indices = tree.query(query_pts)

                    y[nan_and_inside] = vals_known[indices]


        # --- Return grid indices with presence  ---
        return [idx_pos_map[i] for i in np.where(y == 1.0)[0]]




    # ------------- AQs based on MPAEU SDMs -------------

    def locally_rare_features_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
        cut_lrf: int,
        target_col: str = "aq1",
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int], List[int]]:
        """
        AQ1 (LRF) with MPAEU:
        
        Params:
            taxon_ids: WoRMS taxon IDs list.
            assessment_grid: evaluation grid
            cut_lrf: threshold (%) below which the taxon is LRF. Set 100 to include all taxa.
            target_col: column to write results (default 'aq1')

        Returns:
        Tuple containing 1) GeoDataFrame with 'target_col' filled with LRF scores (0-5), 2) list of available IDs, 3) list of skipped IDs, 4) list of LRF IDs.
        """

        results = assessment_grid.copy()
        results["aggregation"] = 0

        included_ids: List[int] = []
        skipped_ids:  List[int] = []
        lrf_ids:      List[int] = []

        total_cells = len(results)

        for taxonid in taxon_ids:
            
            try:
                _, presence, extent, raster_crs = MPAEU_AWS_Utils.fit_regions_prediction(
                    taxonid, self.model, self.method, self.scenario
                )
            except Exception as e:
                skipped_ids.append(taxonid)
                continue

            included_ids.append(taxonid)
            print(f"[{taxonid}] Raster leído correctamente")

            # Presenc cells
            try:
                idxs = self._present_indices_with_nearest_optimized(results, presence, extent, raster_crs)
                coverage_pct = (len(idxs) / total_cells) * 100 if total_cells else 0.0

                if coverage_pct <= cut_lrf:
                    lrf_ids.append(taxonid)

                    if idxs:
                        results.loc[idxs, "aggregation"] += 5
            except Exception as e:
                pass

        den = len(lrf_ids) or 1
        results[target_col] = results["aggregation"] / den

        return (
            results,
            list(dict.fromkeys(included_ids)),
            list(dict.fromkeys(skipped_ids)),
            list(dict.fromkeys(lrf_ids)),
        )
    
    def nationally_rare_feature_presence(
        self,
        taxon_ids: List[int],              
        country_name: str,                 
        grid_size: int,                    
        assessment_grid: gpd.GeoDataFrame, 
        cut_nrf: int,                      
        target_col: str = "aq5",
        eez_path: str = "./results/EVA/world_eez.parquet", 
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int], List[int]]:
        """
        AQ5 (NRF) with MPAEU:
        
        Params:
            taxon_ids: WoRMS taxon IDs list.
            country_name: country name string to filter EEZ
            grid_size: cell size (m) for the EEZ grid
            assessment_grid: evaluation grid
            cut_nrf: threshold (%) below which the taxon is NRF. Set 100 to include all taxa.
            target_col: column to write results (default 'aq1')

        Returns:
        Tuple containing 1) GeoDataFrame with 'target_col' filled with NRF scores (0-5), 2) list of available IDs, 3) list of skipped IDs, 4) list of LRF IDs.
        """

        # --- 1) Prepare country EEZ and eez_grid ---
        eez_file = gpd.read_parquet(eez_path)
        eez_gdf_4326 = eez_file[eez_file["SOVEREIGN1"] == country_name].to_crs(4326)
        if eez_gdf_4326.empty:
            raise ValueError(f"No se encontró EEZ para '{country_name}' en {eez_path}")

        eez_grid = create_quadrat_grid(eez_gdf_4326, grid_size=grid_size)
        results = assessment_grid.copy()
        results["aggregation"] = 0

        included_ids: List[int] = []
        skipped_ids:  List[int] = []
        nrf_ids:      List[int] = []

        total_eez_cells = len(eez_grid)

        for taxonid in taxon_ids:
            # --- 2) Read MPAEU raster (presence returns a numpy array with presence (1), absence (0) and NaN (np.nan) values) ---
            try:
                _, presence, extent, raster_crs = MPAEU_AWS_Utils.fit_regions_prediction(
                    taxonid,
                    self.model,
                    self.method,
                    self.scenario
                )
             
            except Exception:
                skipped_ids.append(taxonid)
                continue

            included_ids.append(taxonid)

            try:
                # --- 3) Check if TaxonID i presence cover on EEZ grid ---
                eez_idxs = self._present_indices(eez_grid, presence, extent, raster_crs)
                coverage_pct = (len(eez_idxs) / total_eez_cells) * 100 if total_eez_cells else 0.0

                if coverage_pct <= cut_nrf:
                    nrf_ids.append(taxonid)
                    ass_idxs = self._present_indices_with_nearest_optimized(results, presence, extent, raster_crs)
                    if ass_idxs:
                        results.loc[ass_idxs, "aggregation"] += 5

            except Exception:
                continue

        den = len(nrf_ids) or 1
        results[target_col] = results["aggregation"] / den

        return (
            results,
            list(dict.fromkeys(included_ids)),
            list(dict.fromkeys(skipped_ids)),
            list(dict.fromkeys(nrf_ids)),
        )


    def feature_number_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
        target_col: str = "aq7",
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int]]:
        """
        AQ7 (FN) with MPAEU (same structure for AQ10, AQ12 & AQ14):
        
        Params:
            taxon_ids: WoRMS taxon IDs list.
            assessment_grid: evaluation grid
            target_col: column to write results (default 'aq1')

        Returns:
        Tuple containing 1) GeoDataFrame with 'target_col' filled with LRF scores (0-5), 2) list of available IDs, 3) list of skipped IDs.
        """
        results = assessment_grid.copy()
        results["aggregation"] = 0

        included_ids: List[int] = []
        skipped_ids:  List[int] = []

        for taxonid in taxon_ids:
            try:
                _, presence, extent, raster_crs = MPAEU_AWS_Utils.fit_regions_prediction(
                    taxonid, self.model, self.method, self.scenario
                )
            except Exception as e:
                skipped_ids.append(taxonid)
                continue

            included_ids.append(taxonid)

            try:
                idxs = self._present_indices_with_nearest_optimized(results, presence, extent, raster_crs)
                if idxs:
                    results.loc[idxs, "aggregation"] += 5
            except Exception as e:
                pass

        den = len(included_ids) or 1
        results[target_col] = results["aggregation"] / den

        return results, list(dict.fromkeys(included_ids)), list(dict.fromkeys(skipped_ids))

    def ecologically_significant_features_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int]]:
        """AQ10 = same as AQ7 but with ESF."""
        return self.feature_number_presence(taxon_ids, assessment_grid, target_col="aq10")

    def habitat_forming_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int]]:
        """AQ12 = same as AQ7 but with HFS/BH."""
        return self.feature_number_presence(taxon_ids, assessment_grid, target_col="aq12")

    def mutualistic_symbiotic_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int]]:
        """AQ14 = same as AQ7 but with MSS."""
        return self.feature_number_presence(taxon_ids, assessment_grid, target_col="aq14")


# --- Dispatcher: requeires an EVA instance, grid + params configuration ---
def run_selected_assessments(
    eva: EVA_MPAEU,              # instance
    grid: gpd.GeoDataFrame,      # assessment grid
    params: Dict[str, Dict],     
) -> gpd.GeoDataFrame:
    function_map = {
        "aq1":  eva.locally_rare_features_presence,
        "aq5":  eva.nationally_rare_feature_presence,
        "aq7":  eva.feature_number_presence,
        "aq10": eva.ecologically_significant_features_presence,
        "aq12": eva.habitat_forming_presence,
        "aq14": eva.mutualistic_symbiotic_presence,
    }

    results = grid.copy()
    for aq_key, func_args in params.items():
        func = function_map.get(aq_key)
        if not func:
            continue
        results, *rest = func(assessment_grid=results, **func_args)
    return results

# ===================
# Testing / examples 
# ===================
if __name__ == "__main__":
    # Study Area .parquet path
    aoi_path = r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.parquet"

    # Create H3 grid at resolution 8
    grid = create_h3_grid(aoi_path, 8)
    # grid = create_quadrat_grid(aoi_path, 10000)  # alternatively, a quadrat grid of 10km cells

    # Taxon IDs for different assessments
    lrf_id_list  = [495082,127165]
    nrf_id_list  = [495082,  145782]
    esf_id_list  = [145092, 145367, 145782]
    hfs_bh_id_list = [145108,  145735]
    mss_id_list  = [495082, 145092]

    fn_ids = lrf_id_list + nrf_id_list + esf_id_list + hfs_bh_id_list + mss_id_list
    all_ids_unique = list(dict.fromkeys(fn_ids))  

    # Create EVA instance with parameters
    eva = EVA_MPAEU(model="mpaeu", method="ensemble", scenario="current_cog") #Check MPAEU project for further model configurations: https://iobis.github.io/mpaeu_docs/datause.html

    params = {
        "aq1":  {"taxon_ids": lrf_id_list, "cut_lrf": 100},
        "aq5":  {"taxon_ids": nrf_id_list, "country_name": "Spain", "grid_size": 10000, "cut_nrf": 100},
        "aq7":  {"taxon_ids": all_ids_unique},
        "aq10": {"taxon_ids": esf_id_list},
        "aq12": {"taxon_ids": hfs_bh_id_list},
        "aq14": {"taxon_ids": mss_id_list},
    }

    # Execute the assessment:
    result = run_selected_assessments(eva=eva, grid=grid, params=params)

    # Save results as parquet file:
    result.to_parquet(os.path.join(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria", "subtidal_macroalgae.parquet"))