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
    print("DEBUG ➔ checking dir:", dirpath)  # traza
    if not os.path.isdir(dirpath):  # validar carpeta
        print("DEBUG ➔ dir not found, aborting")  # traza
        return abort(404)  # 404 si no existe

    cands = glob.glob(os.path.join(dirpath, f"*{year}*.tif")) + glob.glob(os.path.join(dirpath, f"*{year}*.tiff"))  # candidatos
    matches = [p for p in cands if "accretion" not in os.path.basename(p).lower()]  # excluir *_accretion.*
    print("DEBUG ➔ matches (class tifs):", matches)  # traza
    if not matches:  # si vacío
        return abort(404)  # 404

    matches.sort()  # orden fijo
    tif_path = matches[0]  # elegir primero
    print(f"DEBUG ➔ serving PNG for area={area} scenario={scenario} year={year} tif={os.path.basename(tif_path)}")  # traza

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
    fig.savefig(buf, dpi=200, transparent=True, pad_inches=0)  # exportar PNG
    plt.close(fig)  # cerrar figura
    buf.seek(0)  # rebobinar

    return send_file(buf, mimetype="image/png")  # devolver PNG

if __name__ == "__main__":  # arrancar servidor
    app.run(debug=True, host="0.0.0.0", port=8050, dev_tools_ui=False, dev_tools_props_check=False)










# import os
# from pyproj import datadir
# from io import BytesIO

# # Esto localiza la carpeta donde pyproj instaló su proj.db. Si no esta suele haber problemas para que los tiff se muestren como .png en el mapa de leaflet
# os.environ["PROJ_LIB"] = datadir.get_data_dir()

# import rasterio
# from rasterio.vrt import WarpedVRT
# from rasterio.enums import Resampling
# import matplotlib
# matplotlib.use('agg')
# import matplotlib.pyplot as plt
# from matplotlib.colors import ListedColormap, BoundaryNorm
# from flask import send_file, abort
# import glob
# from app import create_app

# app = create_app()

# @app.server.route("/raster/<area>/<scenario>/<int:year>.png")
# def serve_reprojected_raster(area, scenario, year):
    
#     folder_area = area

#     # 2) Construir la ruta a resultados/saltmarshes/<folder_area>/<scenario>/
#     dirpath = os.path.join(
#         os.getcwd(), "results", "saltmarshes",
#         folder_area, scenario
#     )
    
#     print("DEBUG ➔ checking dir:", dirpath)

#     if not os.path.isdir(dirpath):
#         print("DEBUG ➔ dir not found, aborting")
#         return abort(404)

#     # 3) Buscar cualquier TIF que incluya el año en su nombre
#     matches = glob.glob(os.path.join(dirpath, f"*{year}*.tif"))
#     print("DEBUG ➔ matches:", matches)
    
#     if not matches:
#         return abort(404)
#     tif_path = matches[0]

#     # abrimos + creamos un VRT reproyectado a EPSG:4326
#     with rasterio.open(tif_path) as src, \
#          WarpedVRT(src, crs="EPSG:4326", resampling = Resampling.nearest) as vrt:

#         # 2) leemos la banda 1 ya como masked array
#         data = vrt.read(1, masked=True)

#         # 3) sacamos los bounds (lon/lat)
#         b = vrt.bounds
#         lon_min, lon_max = b.left, b.right
#         lat_min, lat_max = b.bottom, b.top

#         w, h = vrt.width, vrt.height

#     # 4) pintamos a color discreto (4 categorías) y transparentamos el nodata
#     colors = ["#8B4513", "#006400", "#636363", "#31C2F3"]
#     cmap  = ListedColormap(colors)
#     norm  = BoundaryNorm([0,1,2,3,4], ncolors=4)

#     # figura al tamaño exacto del VRT
#     fig = plt.figure(frameon=False)
#     fig.set_size_inches(w/200, h/200)  # asumiendo dpi=200
#     ax = fig.add_axes([0,0,1,1])
#     ax.imshow(
#         data,
#         cmap=cmap,
#         norm=norm,
#         extent=(lon_min, lon_max, lat_min, lat_max),
#         interpolation="nearest",
#         origin="upper"
#     )
#     ax.axis("off")

#     buf = BytesIO()
#     fig.savefig(buf, dpi=200, transparent=True, pad_inches=0)
#     plt.close(fig)
#     buf.seek(0)

#     return send_file(buf, mimetype="image/png")

# # 3) Arranca el servidor Dash
# if __name__ == "__main__":
#     app.run(
#         debug=True,
#         host="0.0.0.0",
#         port=8050,
#         dev_tools_ui=False,
#         dev_tools_props_check=False
#     )