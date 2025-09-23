# from pathlib import PurePosixPath
# from geopandas import gpd
# from dataclasses import dataclass
# from typing import Optional
# import rasterio as rio
# import matplotlib.pyplot as plt
# import numpy as np
# import os
# from eva_obis import create_h3_grid, create_quadrat_grid
# import pyproj

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

import math, os, pyproj
import numpy as np
import geopandas as gpd
import rasterio as rio
from shapely.geometry import box
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window
from pathlib import PurePosixPath
from eva_obis import create_h3_grid, create_quadrat_grid

# PROJ del venv (pyproj)
os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()

# Funciones para construir rutas /vsis3/... del S3 bucket publico de MPAEU:
class MPAEU_AWS_Utils:
    @staticmethod
    def get_env_kwargs():
        """Entorno recomendado para S3 público y evitar listados de carpeta"""
        return {
            "AWS_NO_SIGN_REQUEST": "YES",                 # si el bucket es público
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",  # evita listados
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.ovr,.xml,.json",
        }
    
    @staticmethod
    def mpaeu_tif_vsis3(taxonid: int, model: str, method: str, scenario: str) -> str:
        """Construye /vsis3/bucket/path/... para la prediction de distribuciones"""
        base = PurePosixPath("mpaeu-dist/results/species")
        tif_name = f"taxonid={taxonid}_model={model}_method={method}_scen={scenario}.tif"
        key = base / f"taxonid={taxonid}" / f"model={model}" / "predictions" / tif_name
        return f"/vsis3/{key}"
    
    @staticmethod
    def mpaeu_tif_mask_vsis3(taxonid: int, model: str, mask_model: str) -> str:
        """Construye /vsis3/bucket/path/... para la máscara de distribución"""
        base = PurePosixPath("mpaeu-dist/results/species")
        tif_name = f"taxonid={taxonid}_model={mask_model}.tif"
        key = base / f"taxonid={taxonid}" / f"model={model}" / "predictions" / tif_name
        return f"/vsis3/{key}"
    
    @staticmethod
    def native_bound_prediction(taxonid: int, model: str, method: str, scenario: str, presence_threshold: float = 80):
        """Obtiene las native bounds de la predicción y asigna presencia/ausencia usando un umbral fijo de 50"""
        mask_model = "mpaeu_mask_cog"
        predic_path = MPAEU_AWS_Utils.mpaeu_tif_vsis3(taxonid, model, method, scenario)
        mask_path = MPAEU_AWS_Utils.mpaeu_tif_mask_vsis3(taxonid, model, mask_model)
        with rio.Env(**MPAEU_AWS_Utils.get_env_kwargs()):
            with rio.open(predic_path) as src, rio.open(mask_path) as mask:
                prediction = src.read(1, masked=True)
                prediction_mask = mask.read(1, masked=True)
                masked_prediction = np.where(prediction_mask==1, prediction, np.nan)
                masked_presence = np.where(masked_prediction>=presence_threshold, 1, np.where(masked_prediction<presence_threshold, 0, np.nan))
                left, bottom, right, top = src.bounds
                extent = (left, bottom, right, top) 
                return masked_prediction, masked_presence, extent, src.crs
        

@dataclass
class EVA_MPAEU:
    model: str = "mpaeu"
    method: str = "ensemble"
    scenario: str = "current_cog"
    presence_threshold: float = 80.0
    all_touched: bool = True         
    pad_factor: float = 0.5          # “medio píxel” de margen alrededor de cada celda

    # ------------- helpers puros (estáticos) -------------

    @staticmethod
    def _round_clip_window(win: Window, h: int, w: int) -> Optional[Tuple[int, int, int, int]]:
        """Redondea offsets/tamaños a enteros y recorta a los límites del array."""
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

    # ------------- núcleo de cruce raster-celdas -------------

    def _present_indices(
        self,
        grid: gpd.GeoDataFrame,
        presence: np.ndarray,                # array 2D con {1,0,NaN}
        extent: Tuple[float, float, float, float],  # (xmin, ymin, xmax, ymax)
        raster_crs,                          # CRS del raster (rasterio.crs.CRS)
    ) -> List[int]:
        """Devuelve índices de celdas del grid con ≥1 píxel de presencia dentro de la geometría."""
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

    # ------------- AQs basadas en MPAEU (rasters) -------------

    def locally_rare_features_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
        #min_grid_per: int,
        cut_lrf: int,
        target_col: str = "aq1",
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int], List[int]]:
        """
        AQ1 (LRF) con MPAEU:
          - Para cada taxón: celdas con presencia en el assessment_grid.
          - Cobertura = % de celdas con presencia.
          - Si cobertura < min_grid_per → no se considera.
          - Si cobertura < cut_lrf → es LRF: +5 en esas celdas.
          - Media = aggregation / nº de taxones catalogados como LRF.
        """
        results = assessment_grid.copy()
        results["aggregation"] = 0

        included_ids: List[int] = []
        skipped_ids:  List[int] = []
        lrf_ids:      List[int] = []

        total_cells = len(results)

        for taxonid in taxon_ids:
            # leer raster presencia
            try:
                _, presence, extent, raster_crs = MPAEU_AWS_Utils.native_bound_prediction(
                    taxonid, self.model, self.method, self.scenario, presence_threshold=self.presence_threshold
                )
            except Exception as e:
                # print(f"[{taxonid}] ERROR leyendo raster: {e!r}")
                skipped_ids.append(taxonid)
                continue

            included_ids.append(taxonid)

            # celdas con presencia
            try:
                idxs = self._present_indices(results, presence, extent, raster_crs)
                coverage_pct = (len(idxs) / total_cells) * 100 if total_cells else 0.0

                # if coverage_pct < min_grid_per:
                #     continue
                if coverage_pct < cut_lrf:
                    lrf_ids.append(taxonid)
                    if idxs:
                        results.loc[idxs, "aggregation"] += 5
            except Exception as e:
                # print(f"[{taxonid}] ERROR procesando celdas: {e!r}")
                pass

        den = len(lrf_ids) or 1
        results[target_col] = results["aggregation"] / den

        return (
            results,
            list(dict.fromkeys(included_ids)),
            list(dict.fromkeys(skipped_ids)),
            list(dict.fromkeys(lrf_ids)),
        )


    def feature_number_presence(
        self,
        taxon_ids: List[int],
        assessment_grid: gpd.GeoDataFrame,
        target_col: str = "aq7",
    ) -> Tuple[gpd.GeoDataFrame, List[int], List[int]]:
        """
        AQ7 (y base para AQ10/12/14): +5 por celda y taxón si existe ≥1 píxel con presencia en la celda.
        Media = aggregation / nº de taxones incluidos (leídos).
        """
        results = assessment_grid.copy()
        results["aggregation"] = 0

        included_ids: List[int] = []
        skipped_ids:  List[int] = []

        for taxonid in taxon_ids:
            # leer raster presencia
            try:
                _, presence, extent, raster_crs = MPAEU_AWS_Utils.native_bound_prediction(
                    taxonid, self.model, self.method, self.scenario, presence_threshold=self.presence_threshold
                )
            except Exception as e:
                skipped_ids.append(taxonid)
                continue

            included_ids.append(taxonid)

            # celdas con presencia para este taxón
            try:
                idxs = self._present_indices(results, presence, extent, raster_crs)
                if idxs:
                    results.loc[idxs, "aggregation"] += 5
            except Exception as e:
                pass

        den = len(included_ids) or 1
        results[target_col] = results["aggregation"] / den

        return results, list(dict.fromkeys(included_ids)), list(dict.fromkeys(skipped_ids))
    
    


# Ejemplo de uso:
aoi_path = r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.parquet"
grid = create_h3_grid(aoi=aoi_path, h3_resolution=9)
lrf_id_list = [495082]
esf_id_list = [145092, 145367, 145782]
hfs_bh_id_list = [145108, 1659019, 145579, 145540, 182742, 145728, 144020, 145735]
all_ids = esf_id_list + hfs_bh_id_list


# Instancia con tu config (se aplica a todas las AQs)
eva = EVA_MPAEU(model="mpaeu", method="ensemble", scenario="current_cog",
                presence_threshold=80.0, all_touched=True, pad_factor=0.5)

# AQ1
result_gdf, included, skipped, lrfs = eva.locally_rare_features_presence(taxon_ids=lrf_id_list, assessment_grid=grid, cut_lrf=5)

# AQ7
# result_gdf, included, skipped = eva.feature_number_presence(taxon_ids=all_ids, assessment_grid=grid)

print("Incluidos (leídos de S3):", included)
print("Saltados (no en S3 o error):", skipped)
print("Locally Rare Features:", lrfs)

result_gdf.to_parquet(os.path.join (r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria", "subtidal_macroalgae_esf_test_mpaeu.parquet"))