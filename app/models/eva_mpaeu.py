from pathlib import PurePosixPath
from geopandas import gpd
import rasterio as rio
import matplotlib.pyplot as plt
import numpy as np
import os
from eva_obis import create_h3_grid, create_quadrat_grid
import pyproj

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
            
class EVA_MPAEU:
    @staticmethod
    def feature_number_presence_from_mpaeu(
        taxon_ids: list[int],
        assessment_grid: gpd.GeoDataFrame,
        model: str = "mpaeu",
        method: str = "ensemble",
        scenario: str = "current_cog",
        target_col: str = "aq7",
    ) -> tuple[gpd.GeoDataFrame, list[int], list[int]]:
        """
        Computes EVA AQ7 using MPAEU distribution models from AWS S3 public bucket:

        Params:
            taxon_ids:list of WoRMS taxon IDs to include in the calculation
            assessment_grid: GeoDataFrame with hexagonal or square grid cells (with geometry column)
            model: MPAEU model name (default: "mpaeu")
            method: MPAEU method name (default: "ensemble")
            scenario: MPAEU scenario name (default: "current_cog")
            target_col: name of the output column in the assessment_grid (default: "aq7")

        Returns:
            results = GeoDataFrame with the same geometry as assessment_grid and a new column with AQ7 values. 
            included_ids = list of taxon IDs that were available in AWS.
            skipped_ids = list of taxon IDs that were not available or had errors.
        """
        if assessment_grid.crs is None:
            raise ValueError("assessment_grid sin CRS.")

        results = assessment_grid.copy()
        results["aggregation"] = 0

        included_ids: list[int] = []
        skipped_ids: list[int] = []

        from shapely.geometry import box
        from rasterio.features import geometry_mask
        from rasterio.windows import from_bounds, Window
        import math

        def _round_clip_window(win: Window, arr_h: int, arr_w: int):
            r0 = int(math.floor(win.row_off))
            c0 = int(math.floor(win.col_off))
            r1 = r0 + int(math.ceil(win.height))
            c1 = c0 + int(math.ceil(win.width))
            r0 = max(0, r0); c0 = max(0, c0)
            r1 = min(arr_h, r1); c1 = min(arr_w, c1)
            if r1 <= r0 or c1 <= c0:
                return None
            return r0, r1, c0, c1

        for taxonid in taxon_ids:
            # 1) Lectura (decide included vs skipped)
            try:
                _, presence, extent, raster_crs = MPAEU_AWS_Utils.native_bound_prediction(
                    taxonid, model, method, scenario
                )
            except Exception as e:
                print(f"[{taxonid}] ERROR leyendo raster: {e!r}")
                skipped_ids.append(taxonid)
                continue

            included_ids.append(taxonid)

            # 2) Procesado por celdas
            try:
                grid_r = results.to_crs(raster_crs)

                left, bottom, right, top = extent  # (xmin, ymin, xmax, ymax)
                transform = rio.transform.from_bounds(
                    left, bottom, right, top,
                    width=presence.shape[1],
                    height=presence.shape[0]
                )

                # Diagnóstico rápido (opcional)
                # uniq_vals, counts = np.unique(np.nan_to_num(presence, nan=-1.0), return_counts=True)
                # print(f"[{taxonid}] presence uniques (-1=NaN): {dict(zip(uniq_vals.tolist(), counts.tolist()))}")
                if not np.isfinite(presence).any() or (np.nanmax(presence) < 0.5):
                    continue

                raster_bbox = box(left, bottom, right, top)
                aoi_bbox = box(*grid_r.total_bounds)
                if not raster_bbox.intersects(aoi_bbox):
                    print(f"[{taxonid}] AVISO: el raster no solapa con el AOI (CRS={raster_crs}).")
                    continue

                add_idx = []
                H, W = presence.shape
                px = abs(transform.a)         # tamaño de píxel en X (grados/metros)
                py = abs(transform.e)         # tamaño de píxel en Y (positivo)
                pad_x = 0.5 * px              # medio píxel de margen
                pad_y = 0.5 * py

                for idx, geom in zip(grid_r.index, grid_r.geometry):
                    if geom.is_empty or not geom.intersects(raster_bbox):
                        continue

                    # Ventana con pequeño pad para evitar pérdidas por redondeos
                    gxmin, gymin, gxmax, gymax = geom.bounds
                    win = from_bounds(gxmin - pad_x, gymin - pad_y, gxmax + pad_x, gymax + pad_y, transform=transform)
                    rc = _round_clip_window(win, H, W)
                    if rc is None:
                        continue
                    r0, r1, c0, c1 = rc

                    tile = presence[r0:r1, c0:c1]

                    # Máscara geométrica: usa all_touched=True (hex smaller than pixel)
                    win_transform = rio.windows.transform(Window(c0, r0, c1 - c0, r1 - r0), transform)
                    geom_mask = geometry_mask(
                        [geom],
                        out_shape=tile.shape,
                        transform=win_transform,
                        invert=True,
                        all_touched=True  # <<< clave cuando el píxel es grande y el hex pequeño
                    )

                    valid = np.isfinite(tile)
                    pres = (tile >= 0.5) & valid & geom_mask

                    if pres.any():
                        add_idx.append(idx)

                if add_idx:
                    results.loc[add_idx, "aggregation"] += 5

            except Exception as e:
                print(f"[{taxonid}] ERROR procesando celdas: {e!r}")
                continue

        den = len(included_ids) or 1
        results[target_col] = results["aggregation"] / den

        included_ids = list(dict.fromkeys(included_ids))
        skipped_ids  = list(dict.fromkeys(skipped_ids))
        return results, included_ids, skipped_ids




# # Ejemplo de uso:
aoi_path = r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.parquet"
grid = create_h3_grid(aoi=aoi_path, h3_resolution=9)
esf_id_list = [145092, 145367, 145782]
hfs_bh_id_list = [145108, 1659019, 145579, 145540, 182742, 145728, 144020, 145735]
all_ids = esf_id_list + hfs_bh_id_list

result_gdf, included, skipped = feature_number_presence_from_mpaeu(taxon_ids=all_ids, assessment_grid=grid)

print("Incluidos (leídos de S3):", included)
print("Saltados (no en S3 o error):", skipped)

result_gdf.to_parquet(os.path.join (r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria", "subtidal_macroalgae_esf_test_mpaeu.parquet"))
