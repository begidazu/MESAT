import dash_leaflet as dl
from dash import Input, Output
import app  # sólo si necesitas acceso al app aquí
from .tab_callbacks import BOUNDS  # asume que has cargado allí tu JSON de bounds

@app.callback(
    Output("map", "children"),
    Input("study-area-dropdown", "value"),
    Input("scenario-dropdown", "value"),
    Input("year-dropdown", "value"),
)
def update_map(area, scenario, year):
    layers = [dl.TileLayer()]  # fondo base
    if not (area and scenario and year):
        return layers

    # 1) Bounds los podrías cargar desde un JSON precalculado
    bounds = BOUNDS[area][scenario][year]  # [[lat_min, lon_min], [lat_max, lon_max]]

    # 2) Imagen reproyectada on‐the‐fly
    img_url = f"/raster/{area}/{scenario}/{year}.png"
    layers.append(
        dl.ImageOverlay(
            url=img_url,
            bounds=bounds,
            opacity=0.7,
            interactive=False,
        )
    )
    return layers