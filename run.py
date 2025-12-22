import os  # rutas/entorno
from pyproj import datadir  # localizar proj.db
from io import BytesIO  # buffer de salida

os.environ["PROJ_LIB"] = datadir.get_data_dir()  # ajustar PROJ_LIB

import glob  # búsqueda por patrón
import rasterio  # ráster
from rasterio.vrt import WarpedVRT  # reproyección
from rasterio.enums import Resampling  # remuestreo
import matplotlib  # backend offscreen
matplotlib.use('agg')  # backend sin GUI
import matplotlib.pyplot as plt  # dibujo
from matplotlib.colors import ListedColormap, BoundaryNorm  # colores
from flask import send_file, abort  # respuesta http
from app import create_app  # crear app

import threading, time
from pathlib import Path
import shutil, os


# ------------------------------------------------------- LOCAL TEST ----------------------------------------------------------

# # Definimos el tiempo maximo que queramos que se guarden los ficheros subidos por los usuarios:
# TTL_HOURS = int(os.getenv("UPLOADS_TTL_HOURS", "6"))        # el segundo argumento son las horas

# # Definimos cada cuanto tiempo se ejecuta el recolector para borrar las carpetas viejas:
# GC_INTERVAL_MIN = int(os.getenv("UPLOADS_GC_MIN", "30"))    # frecuencia en minutos

# # Funcion para borrar las carpetas viejas de uploads:
# def _gc_uploads_loop(root="uploads"):                       # bucle del recolector
#     ttl = TTL_HOURS * 3600
#     while True:
#         try:
#             now = time.time()
#             base = Path(os.getcwd()) / root
#             if base.exists():
#                 for kind_dir in base.iterdir():             # p.ej. wind/aqua/...
#                     if not kind_dir.is_dir():
#                         continue
#                     for sid_dir in kind_dir.iterdir():      # p.ej. <session_id>/
#                         if not sid_dir.is_dir():
#                             continue
#                         age = now - sid_dir.stat().st_mtime
#                         if age > ttl:                       # carpeta “vieja”
#                             shutil.rmtree(sid_dir, ignore_errors=True)
#         except Exception:
#             pass
#         time.sleep(GC_INTERVAL_MIN * 60)

# # Creamos la instancia de la app dash/flask:
# app = create_app()  

# # Generamos un hilo daemos que se ejecuta en segundo plano que maneja las carpetas viejas:
# threading.Thread(target=_gc_uploads_loop, args=("uploads",), daemon=True).start()


# @app.server.route("/raster/<area>/<scenario>/<int:year>.png")  # endpoint de PNG
# def serve_reprojected_raster(area, scenario, year):  # servir PNG desde tif de clases
#     dirpath = os.path.join(os.getcwd(), "results", "saltmarshes", area, scenario)  # carpeta del escenario
#     if not os.path.isdir(dirpath):  # validar carpeta
#         return abort(404)  # 404 si no existe

#     cands = glob.glob(os.path.join(dirpath, f"*{year}*.tif")) + glob.glob(os.path.join(dirpath, f"*{year}*.tiff"))  # candidatos
#     matches = [p for p in cands if "accretion" not in os.path.basename(p).lower()]  # excluir *_accretion.*
#     if not matches:  # si vacío
#         return abort(404)  # 404

#     matches.sort()  # orden fijo
#     tif_path = matches[0]  # elegir primero

#     with rasterio.open(tif_path) as src, WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.nearest) as vrt:  # VRT a 4326
#         data = vrt.read(1, masked=True)  # leer banda (sin máscara para no esconder clase 0)
#         b = vrt.bounds  # bounds
#         lon_min, lon_max = b.left, b.right  # longitudes
#         lat_min, lat_max = b.bottom, b.top  # latitudes
#         w, h = vrt.width, vrt.height  # tamaño en px

#     colors = ["#8B4513", "#006400", "#636363", "#31C2F3"]  # colores por clase 0..3
#     cmap  = ListedColormap(colors)  # colormap discreto
#     norm  = BoundaryNorm([0,1,2,3,4], ncolors=4)  # normalización por clases

#     fig = plt.figure(frameon=False)  # figura sin marco
#     fig.set_size_inches(w/200, h/200)  # tamaño en pulgadas
#     ax = fig.add_axes([0,0,1,1])  # único eje a pantalla completa
#     ax.imshow(  # dibujar imagen
#         data, cmap=cmap, norm=norm,
#         extent=(lon_min, lon_max, lat_min, lat_max),
#         interpolation="nearest", origin="upper"
#     )
#     ax.axis("off")  # ocultar ejes

#     buf = BytesIO()  # buffer
#     fig.savefig(buf, dpi=100, transparent=True, pad_inches=0)  # exportar PNG
#     plt.close(fig)  # cerrar figura
#     buf.seek(0)  # rebobinar

#     return send_file(buf, mimetype="image/png")  # devolver PNG

# if __name__ == "__main__":  # arrancar servidor en local
#     app.run(debug=True, host="0.0.0.0", port=8050, dev_tools_ui=False, dev_tools_props_check=False)

# ----------------------------------------------------- END LOCAL TEST --------------------------------------------------------




# ---------------------------------------------------- PRODUCTION SERVER ------------------------------------------------------

# WSGI app (Gunicorn importará esto)
app = create_app()
server = app.server  # cómodo para gunicorn: run:server


@server.route("/raster/<area>/<scenario>/<int:year>.png")
def serve_reprojected_raster(area, scenario, year):
    dirpath = os.path.join(os.getcwd(), "results", "saltmarshes", area, scenario)
    if not os.path.isdir(dirpath):
        return abort(404)

    cands = glob.glob(os.path.join(dirpath, f"*{year}*.tif")) + glob.glob(os.path.join(dirpath, f"*{year}*.tiff"))
    matches = [p for p in cands if "accretion" not in os.path.basename(p).lower()]
    if not matches:
        return abort(404)

    matches.sort()
    tif_path = matches[0]

    with rasterio.open(tif_path) as src, WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.nearest) as vrt:
        data = vrt.read(1, masked=True)
        b = vrt.bounds
        lon_min, lon_max = b.left, b.right
        lat_min, lat_max = b.bottom, b.top
        w, h = vrt.width, vrt.height

    colors = ["#8B4513", "#006400", "#636363", "#31C2F3"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm([0, 1, 2, 3, 4], ncolors=4)

    fig = plt.figure(frameon=False)
    fig.set_size_inches(w / 200, h / 200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(
        data, cmap=cmap, norm=norm,
        extent=(lon_min, lon_max, lat_min, lat_max),
        interpolation="nearest", origin="upper"
    )
    ax.axis("off")

    buf = BytesIO()
    fig.savefig(buf, dpi=100, transparent=True, pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")