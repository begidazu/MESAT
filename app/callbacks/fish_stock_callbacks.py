import os, glob  # manejar rutas y buscar archivos
import io  # buffers en memoria
from zipfile import ZipFile  # crear ZIPs
import dash_leaflet as dl  # componentes Leaflet
import rasterio  # lectura ráster
from rasterio.vrt import WarpedVRT  # reproyección al vuelo
from rasterio.enums import Resampling  # remuestreo
from dash import Input, Output, State, html, dcc, callback_context, dash_table  # Dash core
import dash  # tipado de la app
from dash.exceptions import PreventUpdate  # evitar actualizaciones
import dash_bootstrap_components as dbc  # componentes Bootstrap
import matplotlib.pyplot as plt  # dibujar PNGs
import plotly.express as px  # gráficas interactivas
import numpy as np  # numérico
import pandas as pd  # datos tabulares
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
        
        @app.callback(  # reset total
            Output("fish-stocks-dropdown", "value", allow_duplicate=True),
            Output('map', 'viewport', allow_duplicate=True),
            Output("run-fish-button", "disabled", allow_duplicate=True),
            Output("fish-chart", "children", allow_duplicate=True),
            Output("info-button-fish", "hidden", allow_duplicate=True),
            Output("fish-results", "hidden", allow_duplicate=True),
            Input("reset-fish-button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset(n):  # limpiar todo
            if n:
                return [None, {"center": [40, -3.5], "zoom": 7}, True, None, True, True]
            raise PreventUpdate
        
        @app.callback(
            Output("fish-chart", "children"),
            Output("info-button-fish", "hidden"),
            Output("fish-results", "hidden"),
            Input("run-fish-button", "n_clicks"),
            State("fish-stocks-dropdown", "value"),
            prevent_initial_call=True
        )
        def render_fish_table(n, area):  # mostrar tabla al pulsar Run
            if not n or not area:
                raise PreventUpdate

            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            parquet_path = os.path.join(base_dir, "results", "pelagic_fish_stocks", "SPF_accounts_MESIT.parquet")

            try:
                df = pd.read_parquet(parquet_path)
            except Exception as e:
                return html.Div(f"Error reading data: {e}", style={"color": "crimson", "whiteSpace": "pre-wrap"})

            df_filtered = df[df["Stock"] == area].copy()
            if df_filtered.empty:
                return html.Div(f"No records found for stock {area}.", style={"fontStyle": "italic", "color": "#666"})

            table_fieldnames = {
                'Extent': 'Extent (km²)',
                'Condition': 'Condition (0-1)',
                'FP_supply': 'Food Provisioning Supply (tons)',
                'FP_demand': 'Food Provisioning Demand (tons)',
                'FP_balance': 'Food Provisioning Balance (tons)',
            }

            # Construir tabla con estilo consistente y cabeceras mapeadas
            table = dash_table.DataTable(
                id="fish-stock-table",
                columns=[{"name": table_fieldnames.get(c, c), "id": c} for c in df_filtered.columns],
                data=df_filtered.to_dict("records"),
                sort_action="native",
                filter_action="native",
                page_action="none",
                export_headers="display",
                style_table={"maxHeight": "720px", "overflowY": "auto", "border": "1px solid #ddd", "borderRadius": "8px"},
                style_cell={"padding": "8px", "fontSize": "1rem", "textAlign": "center"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f7f7f7", "borderBottom": "1px solid #ccc"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}
                ],
            )
            return [html.Div([html.Hr(), html.H4("Pelagic Fish Stock results"), table], style={"marginTop": "8px"}), False, False]
        
        @app.callback(
             Output("run-fish-button", "disabled"),
             Input("fish-stocks-dropdown", "value"),
            prevent_initial_call=True
        )
        def toggle_run_button(area):  # habilitar botón Run
            return not bool(area)
        
        @app.callback(  # toggle info modal
            Output("info-fish-modal", "is_open"),
            Input("info-button-fish", "n_clicks"),
            Input("info-fish-close", "n_clicks"),
            State("info-fish-modal", "is_open"),
            prevent_initial_call=True
        )
        def toggle_info_modal(info_clicks, close_clicks, is_open):  # abrir/cerrar modal de info
            if not info_clicks and not close_clicks:
                raise PreventUpdate
            return not is_open

