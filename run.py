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

app = create_app()  # instancia Dash/Flask

@app.server.route("/raster/<area>/<scenario>/<int:year>.png")  # endpoint de PNG
def serve_reprojected_raster(area, scenario, year):  # servir PNG desde tif de clases
    dirpath = os.path.join(os.getcwd(), "results", "saltmarshes", area, scenario)  # carpeta del escenario
    if not os.path.isdir(dirpath):  # validar carpeta
        return abort(404)  # 404 si no existe

    cands = glob.glob(os.path.join(dirpath, f"*{year}*.tif")) + glob.glob(os.path.join(dirpath, f"*{year}*.tiff"))  # candidatos
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

if __name__ == "__main__":  # arrancar servidor
    app.run(debug=True, host="0.0.0.0", port=8050, dev_tools_ui=False, dev_tools_props_check=False)
