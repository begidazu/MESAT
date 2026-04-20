import os, glob  # manejar rutas y buscar archivos
import io  # buffers en memoria
from zipfile import ZipFile  # crear ZIPs
import dash_leaflet as dl  # componentes Leaflet
import rasterio  # lectura ráster
from rasterio.vrt import WarpedVRT  # reproyección al vuelo
from rasterio.enums import Resampling  # remuestreo
from dash import Input, Output, State, html, dcc, callback_context  # Dash core
import dash  # tipado de la app
from dash.exceptions import PreventUpdate  # evitar actualizaciones
import dash_bootstrap_components as dbc  # componentes Bootstrap
import matplotlib.pyplot as plt  # dibujar PNGs
import plotly.express as px  # gráficas interactivas
import numpy as np  # numérico
import time, json
import geopandas as gpd

def register_fish_stock_callbacks(app: dash.Dash):
        @app.callback(  # centrar/zoom por área
            Output("map", "viewport", allow_duplicate=True),
            Input("fish-stocks-dropdown", "value"),
            prevent_initial_call=True
        )
        def center_and_zoom(area):  # cambiar viewport
            if not area:
                raise PreventUpdate
            mapping = {
                "ANE8": ([44.663945, -11.054399], 7),
                "ANE9AS": ([36.236357,   -7.843774], 10),
                "PIL8C9A": ([40.128468, -6.292734],  7),
                "HOM9A": ([39.197664, -6.292734],  7),
                "HOMNEA": ([57.777632, 3.036991], 6),
                "MACNEA": ([64.211587, 14.825564], 5)
            }

            center, zoom = mapping[area]
            return {"center": center, "zoom": zoom}