import os  # rutas/entorno
from pyproj import datadir  # localizar proj.db
from io import BytesIO  # buffer de salida

#os.environ["PROJ_LIB"] = datadir.get_data_dir()  # ajustar PROJ_LIB

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
import numpy as np

from PIL import Image
from rasterio.warp import calculate_default_transform
from rasterio.windows import from_bounds

from rasterio.io import MemoryFile
from pyproj import Transformer


# ------------------------------------------------------- LOCAL TEST ----------------------------------------------------------

# Definimos el tiempo maximo que queramos que se guarden los ficheros subidos por los usuarios:
TTL_HOURS = int(os.getenv("UPLOADS_TTL_HOURS", "6"))        # el segundo argumento son las horas

# Definimos cada cuanto tiempo se ejecuta el recolector para borrar las carpetas viejas:
GC_INTERVAL_MIN = int(os.getenv("UPLOADS_GC_MIN", "30"))    # frecuencia en minutos

# Funcion para borrar las carpetas viejas de uploads:
def _gc_uploads_loop(root="uploads"):                       # bucle del recolector
    ttl = TTL_HOURS * 3600
    # --- NUEVO: Base path dinámico para el recolector de basura ---
    BASE_DIR = Path(__file__).resolve().parent
    while True:
        try:
            now = time.time()
            base = BASE_DIR / root
            if base.exists():
                for kind_dir in base.iterdir():             # p.ej. wind/aqua/...
                    if not kind_dir.is_dir():
                        continue
                    for sid_dir in kind_dir.iterdir():      # p.ej. <session_id>/
                        if not sid_dir.is_dir():
                            continue
                        age = now - sid_dir.stat().st_mtime
                        if age > ttl:                       # carpeta “vieja”
                            shutil.rmtree(sid_dir, ignore_errors=True)
        except Exception:
            pass
        time.sleep(GC_INTERVAL_MIN * 60)

# Creamos la instancia de la app dash/flask:
app = create_app()  

# Generamos un hilo daemos que se ejecuta en segundo plano que maneja las carpetas viejas:
threading.Thread(target=_gc_uploads_loop, args=("uploads",), daemon=True).start()


@app.server.route("/raster/<area>/<scenario>/<int:year>.png")  # endpoint de PNG
def serve_reprojected_raster(area, scenario, year):  # servir PNG desde tif de clases
    # --- NUEVO: Base path dinámico para buscar el raster --
    # 
    
    # print("BASE_DIR:", Path(__file__).resolve().parent)  # debug: mostrar base dir
    # print ("here....")

    # dirpath = os.path.join(os.getcwd(), "results", "saltmarshes", area, scenario)

    # print ("Previous dirpath:", dirpath)  # debug: mostrar dirpath antes de join    


    BASE_DIR = Path(__file__).resolve().parent
    dirpath = BASE_DIR / "results" / "saltmarshes" / area / scenario
    
    if not dirpath.is_dir():  # validar carpeta
        return abort(404)  # 404 si no existe

    cands = glob.glob(str(dirpath / f"*{year}*.tif")) + glob.glob(str(dirpath / f"*{year}*.tiff"))  # candidatos
    matches = [p for p in cands if "accretion" not in os.path.basename(p).lower()]  # excluir *_accretion.*
    if not matches:  # si vacío
        return abort(404)  # 404

    matches.sort()  # orden fijo
    tif_path = matches[0]  # elegir primero

    with rasterio.open(tif_path) as src, WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.nearest) as vrt:  # VRT a 4326
        data = vrt.read(1, masked=True)  # leer banda (sin máscara para no esconder clase 0)
        b = vrt.bounds  # bounds
        lon_min, lon_max = b.left, b.right  # longitudes
        lat_min, lat_max = b.bottom, b.top  # latitudes
        w, h = vrt.width, vrt.height  # tamaño en px

    colors = ["#8B4513", "#006400", "#636363", "#31C2F3"]  # colores por clase 0..3
    cmap  = ListedColormap(colors)  # colormap discreto
    norm  = BoundaryNorm([0,1,2,3,4], ncolors=4)  # normalización por clases

    fig = plt.figure(frameon=False)  # figura sin marco
    fig.set_size_inches(w/200, h/200)  # tamaño en pulgadas
    ax = fig.add_axes([0,0,1,1])  # único eje a pantalla completa
    ax.imshow(  # dibujar imagen
        data, cmap=cmap, norm=norm,
        extent=(lon_min, lon_max, lat_min, lat_max),
        interpolation="nearest", origin="upper"
    )
    ax.axis("off")  # ocultar ejes

    buf = BytesIO()  # buffer
    fig.savefig(buf, dpi=100, transparent=True, pad_inches=0)  # exportar PNG
    plt.close(fig)  # cerrar figura
    buf.seek(0)  # rebobinar

    return send_file(buf, mimetype="image/png")  # devolver PNG

@app.server.route("/raster/fish/<area>/<period>.png")
def serve_fish_stock_raster(area, period):
    BASE_DIR = Path(__file__).resolve().parent

    stock_to_taxon = {
        'ANE8':    ('126426', None),
        'ANE9AS':  ('126426', None),
        'PIL8C9A': ('126421', None),
        'HOM9A':   ('126822', '0_05deg'),
        'HOMNEA':  ('126822', '0_25deg'),
        'MACNEA':  ('127023', None)
    }

    AXIS_FLIPPED_STOCKS = {'HOMNEA', 'MACNEA'}

    if area not in stock_to_taxon:
        return abort(404)

    taxonid, resolution = stock_to_taxon[area]

    dirpath = (
        BASE_DIR / "results" / "pelagic_fish_stocks" / "presence_absence"
        / f"taxonid={taxonid}" / "method=ensemble" / "threshold=max_spec_sens"
    )

    if not dirpath.is_dir():
        return abort(404)

    tif_filename = f"{period}_{resolution}.tif" if resolution else f"{period}.tif"
    tif_path = dirpath / tif_filename

    if not tif_path.exists():
        return abort(404)

    try:
        import numpy as np
        from collections import namedtuple
        from pyproj import Transformer as ProjTransformer
        from rasterio.transform import from_bounds as rio_from_bounds
        from rasterio.warp import reproject, Resampling as WarpResampling
        import rasterio.crs

        BBox = namedtuple('BBox', ['left', 'bottom', 'right', 'top'])

        with rasterio.open(str(tif_path)) as src:
            if area in AXIS_FLIPPED_STOCKS:
                nodata = src.nodata if src.nodata is not None else 255
                data_raw = src.read(1)
                orig_h, orig_w = data_raw.shape

                # Extent ORIGINAL completo del TIF (incluyendo hasta 89.875°N)
                lon_min_src, lon_max_src = -45.125, 70.125
                lat_min_orig, lat_max_orig = 34.875, 89.875  # ← extent real del TIF

                # Extent destino clipeado al límite válido de 3857
                lat_min_dst = lat_min_orig
                lat_max_dst = 85.051129

                src_crs = rasterio.crs.CRS.from_wkt(
                    'GEOGCS["WGS 84",DATUM["WGS_1984",'
                    'SPHEROID["WGS 84",6378137,298.257223563]],'
                    'PRIMEM["Greenwich",0],'
                    'UNIT["degree",0.0174532925199433],'
                    'AXIS["Longitude",EAST],'
                    'AXIS["Latitude",NORTH]]'
                )
                dst_crs = rasterio.crs.CRS.from_epsg(3857)

                # src_transform usa el extent ORIGINAL completo
                src_transform = rio_from_bounds(
                    lon_min_src, lat_min_orig,
                    lon_max_src, lat_max_orig,
                    orig_w, orig_h
                )

                # dst bounds clipeados a 3857 válido
                t = ProjTransformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
                x_min, y_min = t.transform(lon_min_src, lat_min_dst)
                x_max, y_max = t.transform(lon_max_src, lat_max_dst)

                dst_w, dst_h = orig_w, orig_h
                dst_transform = rio_from_bounds(x_min, y_min, x_max, y_max, dst_w, dst_h)

                dst_data = np.full((dst_h, dst_w), nodata, dtype=data_raw.dtype)

                reproject(
                    source=data_raw,
                    destination=dst_data,
                    src_transform=src_transform,
                    src_crs=src_crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=WarpResampling.nearest,
                    src_nodata=nodata,
                    dst_nodata=nodata,
                )

                data = np.ma.masked_equal(dst_data, nodata)
                b = BBox(x_min, y_min, x_max, y_max)
                w, h = dst_w, dst_h

            else:
                with WarpedVRT(src, crs="EPSG:3857", resampling=Resampling.nearest) as vrt:
                    data = vrt.read(1, masked=True)
                    b = vrt.bounds
                    w, h = vrt.width, vrt.height

    except Exception as e:
        import traceback
        print(f"[ERROR] serve_fish_stock_raster: {e}")
        traceback.print_exc()
        return abort(500)

    cmap = ListedColormap(["#00008B", "#8B0000"])
    cmap.set_bad(alpha=0)
    norm = BoundaryNorm([-0.5, 0.5, 1.5], ncolors=2)

    dpi = 500
    fig = plt.figure(frameon=False)
    fig.set_size_inches(w / dpi, h / dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    ax.imshow(
        data,
        cmap=cmap,
        norm=norm,
        extent=(b.left, b.right, b.bottom, b.top),
        interpolation="nearest",
        origin="upper",
        aspect="auto",
    )

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":  # arrancar servidor en local
    app.run(debug=False, host="0.0.0.0", port=8050, dev_tools_ui=False, dev_tools_props_check=False)

# ----------------------------------------------------- END LOCAL TEST --------------------------------------------------------




# ---------------------------------------------------- PRODUCTION SERVER ------------------------------------------------------

# # WSGI app (Gunicorn importará esto)
# app = create_app()
# server = app.server  # cómodo para gunicorn: run:server


# @server.route("/raster/<area>/<scenario>/<int:year>.png")
# def serve_reprojected_raster_prod(area, scenario, year):
#     # --- NUEVO: Base path dinámico para producción ---
#     BASE_DIR = Path(__file__).resolve().parent
#     dirpath = BASE_DIR / "results" / "saltmarshes" / area / scenario
#     
#     if not dirpath.is_dir():
#         return abort(404)
# 
#     cands = glob.glob(str(dirpath / f"*{year}*.tif")) + glob.glob(str(dirpath / f"*{year}*.tiff"))
#     matches = [p for p in cands if "accretion" not in os.path.basename(p).lower()]
#     if not matches:
#         return abort(404)
# 
#     matches.sort()
#     tif_path = matches[0]
# 
#     with rasterio.open(tif_path) as src, WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.nearest) as vrt:
#         data = vrt.read(1, masked=True)
#         b = vrt.bounds
#         lon_min, lon_max = b.left, b.right
#         lat_min, lat_max = b.bottom, b.top
#         w, h = vrt.width, vrt.height
# 
#     colors = ["#8B4513", "#006400", "#636363", "#31C2F3"]
#     cmap = ListedColormap(colors)
#     norm = BoundaryNorm([0, 1, 2, 3, 4], ncolors=4)
# 
#     fig = plt.figure(frameon=False)
#     fig.set_size_inches(w / 200, h / 200)
#     ax = fig.add_axes([0, 0, 1, 1])
#     ax.imshow(
#         data, cmap=cmap, norm=norm,
#         extent=(lon_min, lon_max, lat_min, lat_max),
#         interpolation="nearest", origin="upper"
#     )
#     ax.axis("off")
# 
#     buf = BytesIO()
#     fig.savefig(buf, dpi=100, transparent=True, pad_inches=0)
#     plt.close(fig)
#     buf.seek(0)
#     return send_file(buf, mimetype="image/png")