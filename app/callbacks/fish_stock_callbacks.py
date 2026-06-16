import os
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
from pyproj import Transformer

from rasterio.io import MemoryFile
from pyproj import Transformer

# Dictionary to map stocks to their presence/absence raster paths:
pres_abs = {
    'ANE8': "results/pelagic_fish_stocks/presence_absence/taxonid=126426/method=ensemble/threshold=max_spec_sens",
    'ANE9AS': "results/pelagic_fish_stocks/presence_absence/taxonid=126426/method=ensemble/threshold=max_spec_sens",
    'PIL8C9A': "results/pelagic_fish_stocks/presence_absence/taxonid=126421/method=ensemble/threshold=max_spec_sens",
    'HOM9A': "results/pelagic_fish_stocks/presence_absence/taxonid=126822/method=ensemble/threshold=max_spec_sens",
    'HOMNEA': "results/pelagic_fish_stocks/presence_absence/taxonid=126822/method=ensemble/threshold=max_spec_sens",
    'MACNEA': "results/pelagic_fish_stocks/presence_absence/taxonid=127023/method=ensemble/threshold=max_spec_sens"
}

# Dicionary to map specific resolutions for stocks (only HOM and HOMNEA need it):
stock_resolutions = {
    'HOM9A': '0_05deg',
    'HOMNEA': '0_25deg'
}

# Dictionary to map stocks to a specific border color:
stock_colors = {
    'ANE8': '#0764E6',      
    'ANE9AS': '#07E6D9',    
    'PIL8C9A': '#366663',   
    'HOM9A': '#E57A06',     
    'HOMNEA': '#664F36',    
    'MACNEA': '#364A66'     
}

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
            Output('fish-stocks-overlay', 'children', allow_duplicate=True),
            Output('fish-stocks-legend-div', 'hidden', allow_duplicate=True),
            Output('fish-stocks-period-div', 'hidden', allow_duplicate=True),
            Output('fish-stocks-period-div', 'children', allow_duplicate=True),
            Output("fish-stocks-dropdown", "disabled", allow_duplicate=True),
            Output("capa-parquet", "children", allow_duplicate=True),
            Input("reset-fish-button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset(n):  # limpiar todo
            if n:
                return [None, {"center": [40, -3.5], "zoom": 7}, True, None, True, True, [], True, True, [], False, []]
            raise PreventUpdate
        
        @app.callback(
            Output("fish-chart", "children"),
            Output("info-button-fish", "hidden"),
            Output("fish-results", "hidden"),
            Output("fish-stocks-period-div", "hidden"),  # mostrar radio buttons
            Output("fish-stocks-period-div", "children"),  # actualizar contenido de radio buttons
            Output("fish-stocks-dropdown", "disabled", allow_duplicate=True),
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
                return html.Div(f"Error reading data: {e}", style={"color": "crimson", "whiteSpace": "pre-wrap"}), False, False, True, []

            df_filtered = df[df["Stock"] == area].copy()
            if df_filtered.empty:
                return html.Div(f"No records found for stock {area}.", style={"fontStyle": "italic", "color": "#666"}), False, False, True, []

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
            
            # Crear radio buttons dinámicamente
            radio_buttons = html.Div(
                children=[
                    html.Legend(
                        "Select Time Period",
                        className="mt-4"
                    ),
                    dcc.RadioItems(
                        id='fish-stocks-period-radio',
                        options=[
                            {'label': ' 2000-2009', 'value': '2000_2010'},
                            {'label': ' 2010-2019', 'value': '2010_2020'}
                        ],
                        value='2000_2010',
                        inline=False,
                        inputClassName='form-check-input',
                        className='form-check',
                        labelClassName='form-check-label'
                    )
                ]
            )
            
            return [html.Div([html.Hr(), html.H4("Pelagic Fish Stock results"), table], style={"marginTop": "8px"}), False, False, False, radio_buttons, True]
        
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
        
        @app.callback(  # descargar tabla
            Output("fish-download", "data"),
            Input("fish-results", "n_clicks"),
            State("fish-stock-table", "data"),
            State("fish-stocks-dropdown", "value"),
            prevent_initial_call=True
        )
        def download_fish_table(n, table_data, area):  # descargar tabla como CSV
            if not n or not table_data:
                raise PreventUpdate
            
            df = pd.DataFrame(table_data)
            filename = f"fish_stock_{area}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return dcc.send_data_frame(df.to_csv, filename=filename, index=False)


        @app.callback(
            Output('fish-stocks-overlay', 'children'),
            Output('fish-stocks-legend-div', 'hidden'),
            Output('fish-stocks-legend-div', 'children'),
            Input('fish-stocks-period-radio', 'value'),
            State('fish-stocks-dropdown', 'value'),
            prevent_initial_call=True
        )
        def show_fish_stock_overlay(period, area):
            if not area or not period:
                raise PreventUpdate

            AXIS_FLIPPED_STOCKS = {'HOMNEA', 'MACNEA'}

            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            base_path = os.path.join(base_dir, pres_abs[area])

            resolution = stock_resolutions.get(area, '')
            tif_filename = f"{period}_{resolution}.tif" if resolution else f"{period}.tif"
            tif_path = os.path.join(base_path, tif_filename)

            if not os.path.exists(tif_path):
                return [], True, []

            try:
                from pyproj import Transformer as ProjTransformer
                from collections import namedtuple

                BBox = namedtuple('BBox', ['left', 'bottom', 'right', 'top'])

                with rasterio.open(tif_path) as src:
                    if area in AXIS_FLIPPED_STOCKS:
                        # Mismos bounds que usa el servidor — pyproj directo
                        lon_min_src, lon_max_src = -45.125, 70.125
                        lat_min_src, lat_max_src = 34.875, 85.051129

                        t = ProjTransformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
                        x_min, y_min = t.transform(lon_min_src, lat_min_src)
                        x_max, y_max = t.transform(lon_max_src, lat_max_src)
                        bounds_3857 = BBox(x_min, y_min, x_max, y_max)

                    else:
                        with WarpedVRT(src, crs="EPSG:3857", resampling=Resampling.nearest) as vrt:
                            bounds_3857 = vrt.bounds

                # Ambos casos: convertir 3857 → 4326 para Leaflet
                transformer = ProjTransformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
                lon_min, lat_min = transformer.transform(bounds_3857.left, bounds_3857.bottom)
                lon_max, lat_max = transformer.transform(bounds_3857.right, bounds_3857.top)

            except Exception as e:
                print(f"[ERROR] show_fish_stock_overlay: {e}")
                return [], True, []

            url = f"/raster/fish/{area}/{period}.png"

            overlay = dl.ImageOverlay(
                url=url,
                bounds=[[lat_min, lon_min], [lat_max, lon_max]],
                opacity=0.85
            )

            border_color = stock_colors.get(area, "#000000")
            legend_children = [
                html.Div("Fish species presence-absence", style={'fontWeight':'bold','marginBottom':'6px'}),
                html.Div(
                    [
                        html.Div(style={'width':'14px','height':'14px','background':'#8B0000','border':'1px solid #888'}),
                        html.Span("Presence")
                    ], style={'display':'flex', 'alignItems':'center', 'gap':'6px', 'marginBottom':'4px'}
                ),
                html.Div(
                    [
                        html.Div(style={'width':'14px','height':'14px','background':'#00008B','border':'1px solid #888'}),
                        html.Span("Absence")
                    ], style={'display':'flex', 'alignItems':'center', 'gap':'6px', 'marginBottom':'4px'}
                ),
                html.Hr(style={'margin': '8px 0', 'borderColor': '#ccc'}),
                html.Div("Stock", style={'fontWeight':'bold','marginBottom':'6px'}),
                html.Div(
                    [
                        # html.Div(style={'width':'14px','height':'14px','background': border_color, 'border':'1px solid #888'}),
                        html.Div(style={'width':'14px', 'height':'14px', 'background': 'transparent', 'border': f'3px solid {border_color}'}),
                        html.Span(area)
                    ], style={'display':'flex', 'alignItems':'center', 'gap':'6px', 'marginBottom':'4px'}
                )
            ]

            return [overlay], False, legend_children
        
        @app.callback(
            Output("capa-parquet", "children"),
            Input("run-fish-button", "n_clicks"),
            State("fish-stocks-dropdown", "value"),
            prevent_initial_call=True
        )
        def charge_paint_stock_area(trigger_value, area):
            if not trigger_value or not area:
                raise PreventUpdate

            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            parquet_filename = f"{area.lower()}.parquet"
            parquet_path = os.path.join(base_dir, "results", "pelagic_fish_stocks", parquet_filename)

            if not os.path.exists(parquet_path):
                print(f"[WARN] charge_paint_stock_area: parquet not found for stock {area} in {parquet_path}")
                return []

            try:
                gdf = gpd.read_parquet(parquet_path)
            except Exception as e:
                print(f"[ERROR] charge_paint_stock_area: {e}")
                return []

            if gdf.empty:
                return []

            if gdf.crs is None or gdf.crs.to_string() != "EPSG:4326":
                try:
                    gdf = gdf.to_crs("EPSG:4326")
                except Exception as e:
                    print(f"[ERROR] convert CRS to EPSG:4326: {e}")
                    return []

            geojson_data = json.loads(gdf.to_json())
            border_color = stock_colors.get(area, "#000000")

            capa_vectorial = dl.GeoJSON(
                data=geojson_data,
                id="parquet-stock-geojson",
                style={
                    "color": border_color,
                    "weight": 5,
                    "opacity": 1.0,
                    "fillColor": "transparent",
                    "fillOpacity": 0.0
                }
            )

            return [capa_vectorial]


        @app.callback(
            Output('fish-stocks-overlay', 'children', allow_duplicate=True),
            Output('fish-stocks-legend-div', 'hidden', allow_duplicate=True),
            Output('fish-stocks-period-div', 'hidden', allow_duplicate=True),
            Output('fish-stocks-period-div', 'children', allow_duplicate=True),
            Output('fish-stocks-dropdown', 'value', allow_duplicate=True),
            Output('fish-stocks-dropdown', 'disabled', allow_duplicate=True),
            Output('fish-chart', 'children', allow_duplicate=True),
            Output('info-button-fish', 'hidden', allow_duplicate=True),
            Output('fish-results', 'hidden', allow_duplicate=True),
            Output("capa-parquet", "children", allow_duplicate=True),
            Input('tabs', 'value'),
            prevent_initial_call=True
        )
        def clear_fish_on_tab_change(tab_value):
            if tab_value != 'tab-fishstock':
                return [], True, True, [], None, False, None, True, True, []
            raise PreventUpdate