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
    return