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
from matplotlib.colors import ListedColormap, BoundaryNorm  # colores matplotlib
import matplotlib.pyplot as plt  # dibujar PNGs
import plotly.express as px  # gráficas interactivas
import numpy as np  # numérico
import time



def register_opsa_tab_callbacks(app: dash.Dash):

        # This is the callback to zoom-in zoom-out, and Ecosystem Component checkbox update:
        @app.callback(
            Output("map", "viewport", allow_duplicate=True),
            Output("ec-dropdown", "options"),
            Output("ec-dropdown", "disabled"),
            Output('ec', 'hidden'),
            Input("opsa-study-area", "value"),
            prevent_initial_call=True
        )
        def center_and_zoom(area):
            DEFAULT_VIEWPORT = {"center": [48.912724, -1.141208], "zoom": 6}

            if not area:
                return DEFAULT_VIEWPORT, [], True, True

            mapping = {
                "Santander": ([43.553269, -3.71836], 11),
                "North_Sea": ([51.824025,  2.627373], 9),
                "Irish_Sea": ([53.741164, -4.608093], 9),
            }
            center, zoom = mapping.get(area, (DEFAULT_VIEWPORT["center"], DEFAULT_VIEWPORT["zoom"]))

            if area == "Santander":
                ec = ['Angiosperms','Benthic macroinvertebrates','Intertidal macroalgae','Subtidal macroalgae','Benthic habitats']
            elif area == "North_Sea":
                ec = ['Benthic habitats','Macrozoobenthos']
            elif area == "Irish_Sea":
                ec = ['Benthic habitats','Macrozoobenthos','Demersal fish']
            else:
                ec = []

            return {"center": center, "zoom": zoom}, ([{"label": str(y), "value": y} for y in ec]), False, False 
        
        # This is the callback that filters the selected EC and updates them to a LayerGroup:
        # @app.callback(
        #      Output('opsa-layersgroup', ''),
        #      Input('run-eva-button', 'n_clicks'),
        #      State('ec-dropdown', 'value')
        # )
        # def add_layergroup(n, components):
        #     if n:
        #         return 
        #     raise PreventUpdate