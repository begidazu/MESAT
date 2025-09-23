from pathlib import PurePosixPath
import os
import rasterio as rio
import matplotlib.pyplot as plt
import numpy as np

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
    def native_bound_prediction(taxonid: int, model: str, method: str, scenario: str):
        """Obtiene las native bounds de la predicción"""
        mask_model = "mpaeu_mask_cog"
        predic_path = MPAEU_AWS_Utils.mpaeu_tif_vsis3(taxonid, model, method, scenario)
        mask_path = MPAEU_AWS_Utils.mpaeu_tif_mask_vsis3(taxonid, model, mask_model)
        with rio.Env(**MPAEU_AWS_Utils.get_env_kwargs()):
            with rio.open(predic_path) as src, rio.open(mask_path) as mask:
                prediction = src.read(1, masked=True)
                prediction_mask = mask.read(1, masked=True)
                masked_prediction = np.where(prediction_mask==1, prediction, np.nan)
                left, bottom, right, top = src.bounds
                extent = (left, right, bottom, top)
                return masked_prediction, extent
    

# Ejemplo de uso:
my_prediction, extent = MPAEU_AWS_Utils.native_bound_prediction(101160, "mpaeu", "ensemble", "current_cog")

# Plot
plt.figure(figsize=(8, 6))
im = plt.imshow(my_prediction, extent=extent, origin="upper", vmin=0, vmax=100)
plt.colorbar(im, shrink=0.8, label="Band 1")
plt.title("Preview raster (band 1)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.tight_layout()
plt.show()