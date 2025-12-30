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

# =============================
# Constantes y utilidades
# =============================

CLASS_INFO = {  # mapa valor->(etiqueta,color)
    0: ("Mudflat", "#8B4513"),
    1: ("Saltmarsh", "#006400"),
    2: ("Upland Areas", "#636363"),
    3: ("Channel", "#31C2F3")
}
LABEL_TO_COLOR = {name: color for _, (name, color) in CLASS_INFO.items()}  # etiqueta->color
CATEGORY_ORDER = [CLASS_INFO[k][0] for k in sorted(CLASS_INFO.keys())]  # orden fijo de categorías
row_style = {
        'display': 'grid',
        'gridTemplateColumns': '280px 100px 1fr',  # [col1: checklist] [col2: botón] [col3: input]
        'alignItems': 'center',
        'columnGap': '12px',
        'width': '100%',
    }
fg_row_style = {
    'display': 'grid',
    'gridTemplateColumns': 'repeat(3, minmax(0, 1fr))',
    'gap': '12px',
    'alignItems': 'center',
    'justifyItems': 'stretch',
    'width': '100%',
}

def _acc_tif_from_class_tif(class_tif):  # localizar tif de acreción emparejado
    base, ext = os.path.splitext(class_tif)  # separar base y extensión
    acc_path = f"{base}_accretion{ext}"  # ruta esperada exacta
    if os.path.exists(acc_path):  # si existe el esperado
        return acc_path  # devolver ruta
    folder = os.path.dirname(class_tif)  # carpeta del tif de clases
    stem = os.path.basename(base)  # nombre base sin extensión
    hits = glob.glob(os.path.join(folder, f"{stem}*_accretion{ext}"))  # buscar variantes
    return hits[0] if hits else None  # devolver primera coincidencia o None

def _areas_por_habitat(tif_path):  # sumar áreas (ha) por clase
    with rasterio.open(tif_path) as src:  # abrir tif
        arr = src.read(1)  # leer banda 1
        resx, resy = src.res  # resolución de píxel
    pixel_area_m2 = float(abs(resx * resy))  # área de píxel en m²
    valores, cuentas = np.unique(arr, return_counts=True)  # contar por valor
    areas_ha = [float(c * pixel_area_m2 / 10000.0) for v, c in zip(valores, cuentas) if v in CLASS_INFO]  # pasar a ha
    etiquetas = [CLASS_INFO[v][0] for v in valores if v in CLASS_INFO]  # etiquetas legibles
    colores = [CLASS_INFO[v][1] for v in valores if v in CLASS_INFO]  # colores por clase
    return etiquetas, areas_ha, colores  # devolver resultados

def _png_grafico_areas(titulo, etiquetas, valores, colores):  # crear PNG de barras (áreas)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)  # figura
    bars = ax.bar(etiquetas, valores, color=colores)  # barras
    ax.set_title(titulo)  # título
    ax.set_xlabel("Habitat")  # eje X
    ax.set_ylabel("Area (ha)")  # eje Y
    ax.grid(True, alpha=0.3)  # rejilla
    ymax = max(valores) if valores else 0  # máximo
    ax.set_ylim(0, ymax*1.15 if ymax else 1)  # margen superior
    for b, v in zip(bars, valores):  # anotar valores
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.2f}",
                ha="center", va="bottom", fontweight="bold", fontsize=12)
    buf = io.BytesIO()  # buffer
    fig.tight_layout()  # ajustar
    fig.savefig(buf, format="png")  # guardar PNG
    plt.close(fig)  # cerrar
    buf.seek(0)  # rebobinar
    return buf  # devolver buffer

def _accretion_volume_by_class(class_tif, acc_tif):  # calcular volumen acumulado por clase
    with rasterio.open(class_tif) as cls:  # abrir clases
        class_arr = cls.read(1)  # leer banda
    with rasterio.open(acc_tif) as acc:  # abrir acreción
        acc_arr = acc.read(1, masked=True)  # leer con máscara de nodata
        resx, resy = acc.res  # resolución
        pixel_area_m2 = abs(resx * resy)  # área de píxel
    if class_arr.shape != acc_arr.shape:  # validar alineación
        raise ValueError("Class raster and accretion raster are not aligned.")  # error si no coinciden
    acc_filled = np.ma.filled(acc_arr, 0.0)  # rellenar nodata con 0
    sums = np.bincount(class_arr.ravel(), weights=acc_filled.ravel(), minlength=4)  # sumar por clase
    etiquetas, valores = [], []  # listas de salida
    for v in sorted(CLASS_INFO.keys()):  # recorrer clases
        vol_m3 = float(sums[v] * pixel_area_m2)  # convertir a volumen
        if abs(vol_m3) > 1e-9:  # ignorar cero exacto
            etiquetas.append(CLASS_INFO[v][0])  # añadir etiqueta
            valores.append(vol_m3)  # añadir valor
    return etiquetas, valores  # devolver resultados

def _png_grafico_accretion(titulo, etiquetas, valores):  # crear PNG de acreción
    colores = [LABEL_TO_COLOR[e] for e in etiquetas]  # colores por etiqueta
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)  # figura
    bars = ax.bar(etiquetas, valores, color=colores)  # barras
    ax.set_title(titulo)  # título
    ax.set_xlabel("Habitat")  # eje X
    ax.set_ylabel("Accretion volume (m³/year)")  # eje Y
    ax.grid(True, alpha=0.3)  # rejilla
    ymax = max(valores) if valores else 0  # máximo
    ax.set_ylim(0, ymax*1.15 if ymax else 1)  # margen
    for b, v in zip(bars, valores):  # anotar valores
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.2f}",
                ha="center", va="bottom", fontweight="bold", fontsize=12)
    buf = io.BytesIO()  # buffer
    fig.tight_layout()  # ajustar
    fig.savefig(buf, format="png")  # guardar
    plt.close(fig)  # cerrar
    buf.seek(0)  # rebobinar
    return buf  # devolver

# Functions to style the EVA Overscale Modal:
def row3(*cols):
    cols = list(cols)
    while len(cols) < 3:
        cols.append(dbc.Col(html.Div(), md=4))   # Col vacío mantiene el hueco/alineación
    return dbc.Row(cols, className="g-2 mb-2", align="center")

def _legend_item(color: str, label: str) -> html.Div:  # crear un ítem de leyenda con color sólido
    return html.Div(  # contenedor del ítem
        className="legend-item",
        style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '4px'},  # estilo
        children=[  # hijos
            html.Div(style={'width':'14px','height':'14px','background':color,'border':'1px solid #888', 'borderRadius': '50%'}),  # cuadrito color
            html.Span(label)  # texto del ítem
        ]
    )

def _build_training_points_legend() -> html.Div:  # construir la leyenda completa
    colors = ['#8B4513','#006400','#636363','#31C2F3']  # paleta 
    labels = ['Mudflat','Saltmarsh','Upland Areas','Channel']  # etiquetas
    return html.Div(  # contenedor de leyenda
        className="legend",
        children=[
            html.Div("Training Points", style={'fontWeight':'bold','marginBottom':'6px'}),  # título
            *[_legend_item(c, l) for c, l in zip(colors, labels)]  # items de clases
        ]
    )



# =============================
# Registro de callbacks
# =============================

def register_tab_callbacks(app: dash.Dash):  # registrar callbacks
    SCENARIOS = [  # lista de escenarios (carpeta, etiqueta)
        ("regional_rcp45", "Regional RCP4.5"),
        ("regional_rcp85", "Regional RCP8.5"),
        ("global_rcp45",  "Global RCP4.5"),
    ]

    @app.callback(  # render del tab saltmarsh
        Output("tab-content", "children"),
        Input("tabs", "value")
    )
    def render_tab(tab):  # función de renderizado
        key = f"{tab}-{int(time.time()*1000)}"

        if tab == 'tab-fishstock':  # si es el tab de fishstock
            # si tienes una función de layout:
            # return fish_layout(key)
            # mientras tanto, un placeholder:
            return html.Div("Fish Stocks — coming soon", key=key, style={'padding':'20px'})
        
        elif tab == "tab-eva-overscale":
            return html.Div(
                key=key,
                children=[
                    html.Div(
                        id='eva-mpaeu-div',
                        style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},
                        children=[
                            html.Div(
                                id='functional-groups-div',
                                className='d-flex flex-column',
                                children=[
                                    html.Legend(html.B("Assessment Area")),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                html.Button(
                                                    "Draw",
                                                    id="eva-overscale-sa-draw",
                                                    n_clicks=0,
                                                    disabled=False,
                                                    className="btn btn-outline-primary w-100",
                                                ),
                                                xs=12, md=6, 
                                            ),
                                            dbc.Col(
                                                dcc.Upload(
                                                    id="eva-overscale-sa-file",
                                                    multiple=False,
                                                    accept=".geojson,.json,.parquet",
                                                    className="upload-as-input form-control form-control-lg",
                                                    children=html.Div(
                                                        id="eva-overscale-sa-file-label",
                                                        children="Choose json or parquet file"
                                                    ),
                                                    
                                                ),
                                                xs=12, md=6,
                                            ),
                                        ],
                                        className="g-2 mb-2 align-items-center-stretch",
                                    ),
                                    
                                    html.Legend(html.B("Functional Groups Configuration:")),
                                    html.Div(
                                        className="input-group mb-2",
                                        children=[
                                            dcc.Input(
                                                id="fg",
                                                type="text",
                                                placeholder="Add Functional Group",  # usa value en vez de placeholder para medir
                                                readOnly=True,
                                                className="form-control",
                                                style={"width": "70%"},  # NO crecer al 100%
                                            ),
                                            html.Button(
                                                "+",
                                                id="add-functional-group",
                                                n_clicks=0,
                                                className="btn btn-outline-primary",
                                                style={"width": "64px"}  # ancho fijo del botón (48–56px va bien)
                                            ),
                                            dbc.Tooltip(
                                                "Add functional group",  # el texto del hover
                                                target="add-functional-group",  # id del botón al que se engancha
                                                placement="bottom",   # posición del tooltip (top, bottom, left, right)
                                            )
                                        ],
                                    ),

                                    # Div containers to store functional group buttons and tooltips:
                                    html.Div(id = "fg-button-container", className="mt-2 w-100", style=fg_row_style),
                                    html.Div(id = "fg-button-tooltips", className="mt-2 w-100"),

                                    # Modal reutilizable
                                    dbc.Modal(
                                        id="fg-config-modal",
                                        is_open=False,
                                        size="xl",
                                        children=[
                                            dbc.ModalHeader(dbc.ModalTitle(id="fg-modal-title")),
                                            dbc.ModalBody([
                                                html.Div(
                                                    id='acronyms-div',
                                                    children=[
                                                        html.Legend("Acronyms:"),
                                                        html.H5(html.Ul(
                                                            children=[
                                                                html.Li(["LRF: ", "Locally Rare Features"]),
                                                                html.Li(["NRF: ", "Natinally Rare Features"]),
                                                                html.Li(["ESF: ", "Ecollogically Significant Features"]),
                                                                html.Li(["HFS-BH: ", "Habitat Forming Species - Biogenic Habitats"]),
                                                                html.Li(["MSS: ", "Mutualistic or Symbiotic Species"])
                                                            ]
                                                        ))
                                                    ]
                                                ),
                                                html.Legend(html.B("Group Configuration:")),
                                                # inputs de configuración (ejemplo básico)
                                                row3(
                                                    dbc.Col(dbc.Input(id="fg-input-name", type="text", placeholder="Group name"), md=4),
                                                    dbc.Tooltip("Type group name", target="fg-input-name", placement="auto"),
                                                    dbc.Col(dbc.Input(id="fg-input-eez", type="text", placeholder="EEZ country"), md=4),
                                                    dbc.Tooltip("Target EEZ country name", target="fg-input-eez", placement="auto"),
                                                    dbc.Col(dbc.Input(id="fg-input-eez-grid-size", type= "number", placeholder="EEZ grid size", min=10000, max=50000, step=10000), md=4),
                                                    dbc.Tooltip("Target EEZ grid size to evaluate NRF rareness (in m)", target="fg-input-eez-grid-size", placement="auto"),
                                                ),
                                                row3(
                                                    dbc.Col(dbc.Input(id="fg-lrf-taxonid", type="text", placeholder="LRF Taxon IDs"), md=4),
                                                    dbc.Tooltip("LRF taxon ID list, separated by commas", target="fg-lrf-taxonid", placement="auto"),
                                                    dbc.Col(dbc.Input(id="fg-lrf-threshold", type= "number", placeholder="LRF threshold (%)", min=0, max=100, step=1), md=4),
                                                    dbc.Tooltip("Percentage of grid cells to consider a taxon as LRF or not", target="fg-lrf-threshold", placement="auto"),
                                                ),
                                                row3(
                                                    dbc.Col(dbc.Input(id="fg-nrf-taxonid", type="text", placeholder="NRF Taxon IDs"), md=4),
                                                    dbc.Tooltip("NRF taxon ID list, separated by commas", target="fg-nrf-taxonid", placement="auto"),
                                                    dbc.Col(dbc.Input(id="fg-nrf-threshold", type= "number", placeholder="NRF threshold (%)", min=0, max=100, step=1), md=4),
                                                    dbc.Tooltip("Percentage of grid cells over the EEZ grid to consider a taxon as NRF or not", target="fg-nrf-threshold", placement="auto"),
                                                ),
                                                row3(
                                                    dbc.Col(dbc.Input(id="fg-esf-taxonid", type="text", placeholder="ESF Taxon IDs"), md=4),
                                                    dbc.Tooltip("ESF taxon ID list, separated by commas", target="fg-esf-taxonid", placement="auto"),
                                                    dbc.Col(dbc.Input(id="fg-hfsbh-taxonid", type="text", placeholder="HFS-BH Taxon IDs"), md=4),
                                                    dbc.Tooltip("HFSBH taxon ID list, separated by commas", target="fg-hfsbh-taxonid", placement="auto"),
                                                    dbc.Col(dbc.Input(id="fg-mss-taxonid", type= "text", placeholder="MSS Taxon IDs"), md=4),
                                                    dbc.Tooltip("MSS taxon ID list, separated by commas", target="fg-mss-taxonid", placement="auto"),
                                                )
                                            ]),
                                            dbc.ModalFooter([
                                                dbc.Button("Save", id="fg-modal-save", n_clicks=0, className="btn btn-primary"),
                                                dbc.Button("Close", id="fg-modal-close", n_clicks=0, className="ms-2")
                                            ])
                                        ], scrollable=True, centered= True
                                    )
                                    
                                ]
                            ),

                            html.Div(
                                id='grid-config-div',
                                children=[
                                    html.Legend(html.B("Assessment Grid Configuration:")),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dcc.RadioItems(
                                                    id="opt-radio",
                                                    options=[
                                                        {"label": " Hexagonal H3 Grid", "value": "h3"},
                                                        {"label": " Quadrat Grid", "value": "quadrat"},
                                                    ],
                                                    value="h3",
                                                    className="d-flex flex-column gap-2",
                                                    inputClassName="form-check-input",
                                                    labelClassName="form-check-label",
                                                ),
                                                xs=12, md=6,
                                            ), 
                                            dbc.Col(
                                                html.Div(
                                                    [
                                                        dcc.Input(
                                                            id='eva-overscale-h3-level',
                                                            type="number", min=5, max=7, step=1,
                                                            placeholder="H3 Grid Level",
                                                            className="form-control mb-2",
                                                            disabled=False
                                                        ),
                                                        dbc.Tooltip(
                                                            "H3 Level. Decreasing cell size from 5 to 7",
                                                            target="eva-overscale-h3-level", placement="auto"
                                                        ),
                                                        dcc.Input(
                                                            id='eva-overscale-quadrat-size',
                                                            type="number", min=250, max=5000, step=250,
                                                            placeholder="Quadrat Grid Size in meters",
                                                            className="form-control",
                                                            disabled=True
                                                        ),
                                                        dbc.Tooltip(
                                                            "Quadrat grid size. Min 250, max 5000. Use multiples of 250",
                                                            target="eva-overscale-quadrat-size", placement="auto"
                                                        ),
                                                    ],
                                                    className="w-100"
                                                ),
                                                xs=12, md=6,
                                            ),
                                        ],
                                        className="g-3 align-items-start" 
                                    ),
                                ]
                            ),

                            # Assessment Grid Size store:
                            dcc.Store(id="ag-size-store"),


                            # Run, Download and Info buttons:
                            dcc.Loading(
                                type="dot",  # tipo de spinner
                                color='#2c3e50',
                                children = [
                                    html.Div(
                                        id='eva-overscale-button-bar',
                                        style={'display':'flex','justifyContent':'center','alignItems':'center','verticalAlign':'middle','gap':'12px', "marginTop": "20px"},
                                        children=[
                                            html.Button(  # botón Run
                                                html.Span("Run"),
                                                id="eva-overscale-run-button",
                                                n_clicks=0,
                                                disabled=True,
                                                className='btn btn-outline-primary'  
                                            ),
                                            html.Button(  # botón Reset
                                                html.Span("Reset"),
                                                id="eva-overscale-reset-button",
                                                n_clicks=0,
                                                className='btn btn-outline-primary',
                                                disabled=False
                                            ),
                                            html.Div(  # contenedor de descarga
                                                [
                                                    html.Button(  # botón de descarga
                                                        id='eva-overscale-results',
                                                        disabled=True,
                                                        children=[html.Img(src='/assets/logos/download.png', style={'width':'32px','height':'32px'}), html.Span("Download")],
                                                        n_clicks=0,  # contador
                                                        className='btn btn-outline-primary'
                                                    ),
                                                    dcc.Store(id="eva-results-store"),
                                                    dcc.Download(id='eva-overscale-download')  # componente de descarga
                                                ]
                                            ),
                                            html.Button(  # botón info
                                                [html.Img(src='/assets/logos/info.png', style={'width':'32px','height':'32px', }), html.Span("Info")],
                                                id='eva-overscale-info-button',
                                                className='btn btn-outline-primary',
                                                n_clicks=0  # contador
                                            )
                                        ]
                                    ),
                                ] 
                            ),


                            # html.Div(
                            #     id='eva-overscale-button-bar',
                            #     style={'display':'flex','justifyContent':'center','alignItems':'center','verticalAlign':'middle','gap':'12px', "marginTop": "20px"},
                            #     children=[
                            #         html.Button(  # botón Run
                            #             html.Span("Run"),
                            #             id="eva-overscale-run-button",
                            #             n_clicks=0,
                            #             disabled=True,
                            #             className='btn btn-outline-primary'  
                            #         ),
                            #         html.Button(  # botón Reset
                            #             html.Span("Reset"),
                            #             id="eva-overscale-reset-button",
                            #             n_clicks=0,
                            #             className='btn btn-outline-primary',
                            #             disabled=False
                            #         ),
                            #         html.Div(  # contenedor de descarga
                            #             [
                            #                 html.Button(  # botón de descarga
                            #                     id='eva-overscale-results',
                            #                     disabled=True,
                            #                     children=[html.Img(src='/assets/logos/download.png', style={'width':'32px','height':'32px'}), html.Span("Download")],
                            #                     n_clicks=0,  # contador
                            #                     className='btn btn-outline-primary'
                            #                 ),
                            #                 dcc.Store(id="eva-results-store"),
                            #                 dcc.Download(id='eva-overscale-download')  # componente de descarga
                            #             ]
                            #         ),
                            #         html.Button(  # botón info
                            #             [html.Img(src='/assets/logos/info.png', style={'width':'32px','height':'32px', }), html.Span("Info")],
                            #             id='eva-overscale-info-button',
                            #             className='btn btn-outline-primary',
                            #             n_clicks=0  # contador
                            #         )
                            #     ]
                            # ),

                            html.Div(
                                id = 'area-selection-div',
                                children = [

                                ]
                            ),
                            html.Div(
                                id = 'buttons-div',
                                children = [

                                ]
                            ),

                            # Test button to download functional group configuration as JSON:


                        ]
                    )

                ],
                style={'padding':'20px'})
        
        elif tab == "tab-physical":
            # return physical_layout(key)
            return html.Div(
                key=key,
                children=[
                    html.Div(
                        style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},
                        children=[
                            dcc.Dropdown(
                                id='opsa-study-area',
                                options=[
                                    {'label': 'Santander Coast', 'value': 'Santander'},
                                    {'label': 'North Sea', 'value': 'North_Sea'},
                                    {'label': 'Irish Sea', 'value': 'Irish_Sea'}
                                ],
                                placeholder= 'Select Study Area',
                                className='dropdown-text',
                                searchable=False
                            ),
                            html.Div(
                                id='ec',
                                hidden= True,
                                children=[
                                    html.Legend("Select Ecosystem Components to assess ecosystem condition", className='mt-4'),
                                    dcc.Checklist(id= 'ec-dropdown', options=[], value=[], labelClassName='form-check-label', inputClassName='form-check-input', className='form-check'),
                                    html.Div(  # fila de botones
                                        style={'display':'flex','gap':'10px','alignItems':'center', 'padding-top': '1.5%'},  # estilos
                                        children=[  # hijos
                                            html.Button(  # botón Run
                                                html.Span("Run OPSA"),  # texto
                                                id="run-eva-button",  # id
                                                n_clicks=0,  # contador
                                                disabled=True,  # deshabilitado al inicio
                                                className='btn btn-outline-primary'  # clase css
                                                #style={'width':'100px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}  # estilo
                                            ),
                                            html.Button(  # botón Reset
                                                html.Span("Reset"),  # texto
                                                id="reset-eva-button",  # id
                                                n_clicks=0,  # contador
                                                className='btn btn-outline-primary',  # clase css
                                                disabled=False  # deshabilitado al inicio
                                            )
                                        ]
                                    )
                                ]                             
                            ) 
                        ]
                    ),
                    dcc.Loading(  # contenedor con spinner
                        id="loading-opsa",  # id
                        type="dot",  # tipo de spinner
                        color='#2c3e50',
                        children=[  # hijos
                            #html.Legend("Ocean Physical Stock Account compilation: summary by habitat type", className='mt-4', id='opsa-legend', hidden=True),
                            html.Div(id="opsa-chart", style={'marginTop':'20px'}),
                            html.Div(  # barra inferior
                                    id='button-bar-opsa',  # id
                                    style={'display':'flex','justifyContent':'center','alignItems':'center','verticalAlign':'middle','gap':'12px', 'padding': '20px'},  # estilos
                                    children=[  # hijos
                                        html.Button(  # botón info
                                            [html.Img(src='/assets/logos/info.png', style={'width':'20px','height':'20px'}), html.Span("Ocean Physycal Stock Account compilation info")],  # contenido
                                            id='info-button-opsa',  # id
                                            className='btn btn-outline-primary',
                                            hidden=True,  # oculto al inicio
                                            n_clicks=0  # contador
                                        ),
                                        html.Div(  # contenedor de descarga
                                            [
                                                html.Button(  # botón de descarga
                                                    [html.Img(src='/assets/logos/download.png', style={'width':'20px','height':'20px'}), html.Span("Download results")],  # contenido
                                                    id='opsa-results',  # id
                                                    hidden=True,  # oculto al inicio
                                                    n_clicks=0,  # contador
                                                    className='btn btn-outline-primary'
                                                ),
                                                dcc.Download(id='opsa-download')  # componente de descarga
                                            ]
                                        )
                                    ]
                                )
                            ],  # contenedor de gráficas
                            
                    ),
                    dbc.Modal(  # modal de información
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Ocean Physical Stock Account compilation")),  # cabecera
                            dbc.ModalBody(  # cuerpo
                                 html.Div(
                                    [
                                        # 1) Texto introductorio
                                        html.P([
                                            "The ", html.B("System of Environmental–Economic Accounting – Ecosystem Accounting (SEEA-EA)"),
                                            " is the globally adopted statistical standard that organises biophysical information on ecosystems and ecosystem services, tracks changes in ecosystem extent and condition, and links this information to human activities. SEEA-EA accounts are divided into two subgroups — stock and flow accounts — that are further categorised into physical or monetary accounts."
                                        ], className="mb-3", style={"textAlign": "justify"}),

                                        # 2) Imagen centrada + pie
                                        html.Figure(
                                            [
                                                html.Img(
                                                    src="/assets/images/SEEA.png",
                                                    alt="SEEA-EA framework diagram",
                                                    style={"maxWidth": "100%", "height": "auto"}  # responsive
                                                ),
                                                html.Figcaption(
                                                    "adopted from SEEA-EA framework (UN, 2021).",
                                                    className="text-muted mt-1",
                                                    style={"fontSize": "var(--font-sm)"}          # opcional
                                                ),
                                            ],
                                            className="text-center my-3"  # margen vertical + centrado
                                        ),

                                        # 3) Texto posterior (y lo que necesites debajo)
                                        html.P(
                                            "Physical stock accounts are composed of ecosystem extent and ecosystem condition. In this tab we present the Ocean Physical Stock Accounts (OPSA) compilation for the three study areas assessed in the Ph.D according to the EUNIS habitat (version 2012) classification. It is important to highlight that for OPSA condition assessment user must include all ecosystem components for complete condition indicators. However, if you want to see OPSA assessment taking into account particular ecosystem components, you can select them in the checklist",
                                            className="mb-2", style={"textAlign": "justify"}
                                        ),
                                        html.P(
                                            html.I("*Notice that you can assess ecosystem condition by EUNIS habitat type selecting the target ecosystem component in the checklist."),
                                            className="mb-2", style={"textAlign": "justify"}
                                        ),
                                    ]
                                )
                            ),
                            dbc.ModalFooter(dbc.Button("Close", className="ml-auto", id="info-opsa-close", n_clicks=0)) 
                        ],
                        id="info-opsa-modal", is_open=False, size="xl", centered=True, backdrop=True, scrollable=True # props
                    )




                ], style={'padding':'20px'})
        
        elif tab == "tab-management":
            # return management_layout(key)            
            return html.Div(
                key=key,
                children=[
                    html.Legend("In wich study area you want to simulate?"),
                    html.Div(
                        style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},  # estilos
                        children=dcc.Dropdown(
                                id="mgmt-study-area-dropdown",  # id
                                options=[  # opciones
                                    {"label":"Santander Coast", "value": "Santander"},
                                    {"label":"North Sea", "value":"North_Sea"},
                                    {"label":"Irish Sea", "value": "Irish_Sea"},
                                    {"label":"Urdaibai Estuary","value":"Urdaibai_Estuary"},
                                    {"label":"Cadiz Bay","value":"Cadiz_Bay"},
                                ],
                                placeholder="Select Study Area",  # ayuda
                                className='dropdown-text',  # clase css,
                                searchable=False
                        )
                    ),
                    html.Legend("What economic activity you want to establish?", style={'display':'flex', 'marginTop':'25px'}),
                    html.Div(
                        id='activity-checklist',
                        style={'display': 'flex', 'flexDirection': 'column', 'gap': '15px', 'width': '100%'},
                        children=[

                            html.Div(
                                id="wind-farm-div",
                                style=row_style,
                                children=[
                                    dbc.Checklist(
                                        id='wind-farm',
                                        options=[{"label": "Wind Farm", "value": "wind_farm", "disabled" : True}],
                                        value=[], inline=True, style={'margin': '0'}
                                    ),
                                    html.Button("Draw", id='wind-farm-draw', n_clicks=0, disabled=True,
                                                className='btn btn-outline-warning', style={'width': '100%'}),
                                    dcc.Upload(                                                      # componente para subir ficheros
                                        id="wind-farm-file",                                         # id del upload
                                        multiple=False,                                              # un único fichero
                                        accept="",                                                   # permitir cualquier tipo (validamos en callback)
                                        style={'width': '100%', 'marginLeft': '25px'},
                                        className="upload-as-input form-control form-control-lg",    # clases base (borde, etc.)
                                        children=html.Div(id="wind-farm-file-label")                 # etiqueta visible                                                                                                                 
                                    )

                                ]
                            ),

                            html.Div(
                                id="aquaculture-div",
                                style=row_style,
                                children=[
                                    dbc.Checklist(
                                        id='aquaculture',
                                        options=[{"label": "Aquaculture", "value": "aquaculture", "disabled" : True}],
                                        value=[], inline=True, style={'margin': '0', 'width': '100%'}
                                    ),
                                    html.Button("Draw", id='aquaculture-draw', n_clicks=0, disabled=True,
                                                className='btn btn-outline-success', style={'width': '100%'}),
                                    dcc.Upload(
                                        id='aquaculture-file', 
                                        multiple=False,
                                        accept="",
                                        style={'width': '100%', 'marginLeft': '25px'},
                                        className="upload-as-input form-control form-control-lg",
                                        children=html.Div(id="aquaculture-file-label")                                       
                                        )
                                ]
                            ),

                            html.Div(
                                id="vessel-div",
                                style=row_style,
                                children=[
                                    dbc.Checklist(
                                        id='vessel',
                                        options=[{"label": "New Vessel Route", "value": "new_vessel_route", "disabled" : True}],
                                        value=[], style={'margin': '0'}
                                    ),
                                    html.Button("Draw", id='vessel-draw', n_clicks=0, disabled=True,
                                                className='btn btn-outline-info', style={'width': '100%'}),
                                    dcc.Upload(
                                        id='vessel-file',
                                        multiple=False,
                                        accept="",
                                        style={'width': '100%', 'marginLeft': '25px'},
                                        className="upload-as-input form-control form-control-lg",
                                        children=html.Div(id="vessel-file-label")                                        
                                    )
                                ]
                            ),

                            html.Div(
                                id="defence-div",
                                style=row_style,
                                children=[
                                    dbc.Checklist(
                                        id='defence',
                                        options=[{"label": "Defence", "value": "defence", "disabled" : True}],
                                        value=[], inline=True, style={'margin': '0'}
                                    ),
                                    html.Button("Draw", id='defence-draw', n_clicks=0, disabled=True,
                                                className='btn btn-outline-danger', style={'width': '100%'}),
                                    dcc.Upload(
                                        id='defence-file',
                                        multiple=False,
                                        accept="",
                                        style={'width': '100%', 'marginLeft': '25px'},
                                        className="upload-as-input form-control form-control-lg",
                                        children=html.Div(id="defence-file-label")                                        
                                        )
                                ]
                            ),
                        ]
                    ),
                    html.Div(  # fila de botones
                        style={'display':'flex','gap':'10px','alignItems':'center', 'marginTop':'25px'},  # estilos
                        children=[  # hijos
                            html.Button(  # botón Run
                                html.Span("Run"),  # texto
                                id="mgmt-run-button",  # id
                                n_clicks=0,  # contador
                                disabled=True,  # deshabilitado al inicio
                                className='btn btn-outline-primary'  # clase css
                                #style={'width':'100px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}  # estilo
                            ),
                            html.Button(  # botón Reset
                                html.Span("Reset"),  # texto
                                id="mgmt-reset-button",  # id
                                n_clicks=0,  # contador
                                className='btn btn-outline-primary',  # clase css
                                disabled=True  # deshabilitado al inicio
                            )
                        ]
                    ),
                    dcc.Loading(
                        id="loading'mgmt",
                        type="dot",
                        color='#2c3e50',
                        children=[
                            html.Legend("Economic activities affection to ecosystems", className="mt-4", id="mgmt-legend-affection", hidden=True),
                            html.Div(id="mgmt-table", style={'marginTop': '20px'}),
                            html.Div(
                                id='mgmt-button-bar',
                                style={'display':'flex','justifyContent':'center','alignItems':'center','verticalAlign':'middle','gap':'12px', "marginTop": "20px"},
                                children=[
                                    html.Button(  # botón info
                                        [html.Img(src='/assets/logos/info.png', style={'width':'32px','height':'32px', }), html.Span("Management scenarios info")],
                                        id='mgmt-info-button',  # id
                                        className='btn btn-outline-primary',
                                        hidden=True,  # oculto al inicio
                                        n_clicks=0  # contador
                                    ),
                                    html.Div(  # contenedor de descarga
                                        [
                                            html.Button(  # botón de descarga
                                                [html.Img(src='/assets/logos/download.png', style={'width':'32px','height':'32px'}), html.Span("Download results")], 
                                                id='mgmt-results',  # id
                                                hidden=True,  # oculto al inicio
                                                n_clicks=0,  # contador
                                                className='btn btn-outline-primary'
                                            ),
                                            dcc.Download(id='mgmt-download')  # componente de descarga
                                        ]
                                    ),
                                    html.Button(
                                        html.Span(["➜ ", "Climate Change scenarios"]),  # texto
                                        id="mgmt-scenarios-button",  # id
                                        n_clicks=0,  # contador
                                        className='btn btn-outline-primary',  # clase css
                                        hidden=True
                                    ),
                                    html.Button(
                                        html.Span(["➜ ", "Current situation"]),  # texto
                                        id="mgmt-current-button",  # id
                                        n_clicks=0,  # contador
                                        className='btn btn-outline-primary',  # clase css
                                        hidden=True
                                    ),
                                ]
                            )
                        ]   
                    )
                ], style={'padding':'20px'})

        elif tab == 'tab-saltmarsh':
            return html.Div(
                key= key, 
                children=[  # UI del tab
                    html.Div(  # panel de selects y botones
                        style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},  # estilos
                        children=[  # hijos del panel
                            dcc.Dropdown(  # selector de área
                                id="study-area-dropdown",  # id
                                options=[  # opciones
                                    {"label":"Urdaibai Estuary","value":"Urdaibai_Estuary"},
                                    {"label":"Bay of Santander","value":"Bay_of_Santander"},
                                    {"label":"Cadiz Bay","value":"Cadiz_Bay"},
                                ],
                                placeholder="Select Study Area",  # ayuda
                                className='dropdown-text',  # clase css,
                                searchable=False
                            ),
                            dcc.Dropdown(  # selector de año
                                id="year-dropdown",  # id
                                options=[],  # sin opciones hasta elegir área
                                placeholder="Year",  # ayuda
                                className="dropdown-text",  # clase css
                                disabled=True,  # deshabilitado hasta elegir área
                                searchable=False
                            ),
                            html.Div(  # fila de botones
                                style={'display':'flex','gap':'10px','alignItems':'center'},  # estilos
                                children=[  # hijos
                                    html.Button(  # botón Run
                                        html.Span("Run"),  # texto
                                        id="run-button",  # id
                                        n_clicks=0,  # contador
                                        disabled=True,  # deshabilitado al inicio
                                        className='btn btn-outline-primary'  # clase css
                                        #style={'width':'100px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}  # estilo
                                    ),
                                    html.Button(  # botón Reset
                                        html.Span("Restart"),  # texto
                                        id="reset-button",  # id
                                        n_clicks=0,  # contador
                                        className='btn btn-outline-primary',  # clase css
                                        disabled=True  # deshabilitado al inicio
                                    )
                                ]
                            ),

                            html.Div(
                                id='scenario-checklist-div',
                                hidden = True,
                                children=[
                                    html.Legend(
                                        "Select Climate Change Scenario Map",
                                        className="mt-4"  # aquí la clase que quieras (Bootstrap o CSS propio)
                                    ),
                                    dcc.RadioItems(
                                        id='scenario-radio',
                                        options=[
                                            {'label': 'Regional RCP4.5', 'value': 'reg45'},
                                            {'label': 'Regional RCP8.5', 'value': 'reg85'},
                                            {'label': 'Global RCP4.5',  'value': 'glo45'},
                                        ],
                                        value='reg45',
                                        inline=False,
                                        inputClassName= 'form-check-input',
                                        className= 'form-check',
                                        labelClassName= 'form-check-label'

                                        
                                    )
                                ]
                            )
                        ]
                    ),
                    dcc.Loading(  # contenedor con spinner
                        id="loading",  # id
                        type="dot",  # tipo de spinner
                        color='#2c3e50',
                        children=[  # hijos
                            html.Legend("Habitat distribution and accretion statistics", className='mt-4', id='saltmarsh-legend', hidden=True),
                            html.Div(id="saltmarsh-chart", style={'marginTop':'20px'}),  # contenedor de gráficas
                            html.Div(  # barra inferior
                                id='button-bar',  # id
                                style={'display':'flex','justifyContent':'center','alignItems':'center','verticalAlign':'middle','gap':'12px'},  # estilos
                                children=[  # hijos
                                    html.Button(  # botón info
                                        [html.Img(src='/assets/logos/info.png', style={'width':'20px','height':'20px'}), html.Span("Habitat and accretion info")],  # contenido
                                        id='info-button',  # id
                                        className='btn btn-outline-primary',
                                        hidden=True,  # oculto al inicio
                                        n_clicks=0  # contador
                                    ),
                                    html.Div(  # contenedor de descarga
                                        [
                                            html.Button(  # botón de descarga
                                                [html.Img(src='/assets/logos/download.png', style={'width':'20px','height':'20px'}), html.Span("Download results")],  # contenido
                                                id='marsh-results',  # id
                                                hidden=True,  # oculto al inicio
                                                n_clicks=0,  # contador
                                                className='btn btn-outline-primary'
                                            ),
                                            dcc.Download(id='saltmarsh-download')  # componente de descarga
                                        ]
                                    )
                                ]
                            )
                        ]
                    ),
                    dbc.Modal(  # modal de información
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Habitat & accretion information")),  # cabecera
                            dbc.ModalBody(  # cuerpo
                                html.Ul([
                                        html.Li([html.B("Mudflat: "), html.I("Mudflats")," represent an important part of coastal wetlands, which, like marshes, provide a wide range of ecosystem services such as coastal defence and carbon sequestration."]),  # info Mudflat
                                        html.Li([html.B("Saltmarsh: "), html.I("Saltmarshes"), " are coastal wetlands characterized by its low-lying, flat, and poorly drained soil that is regularly or occasionally flooded by salty or brackish water. Like Mudflats, saltmarshes provide a wide range of ecosystem services such as coastal defence, carbon sequestration and food provisioning."]),  # info Saltmarsh
                                        html.Li([html.B("Upland Areas: "), html.I("Upland Areas"), " represent non-flooded areas where marshes can migrate during sea level rise conditions."]),  # info Upland
                                        html.Li([html.B("Channel: "), html.I("Channels"), " are key features of wetlands that control fundamental dynamics like sediment availability, nutrient circulation and hydrodynamics."]),  # info Channel
                                        html.Li([html.B("Accretion: "), html.I("Accretion"), " is the process where the elevation of a saltmarsh surface increases over time, either by the accumulation of mineral sediments (like silt and clay) or by the buildup of organic matter from decaying plant material. Through ", html.I("accretion"), ", saltmarshes sequester carbon from both accumulation of mineral sediments and organic matter from decaying plant material. "]) # info Accretion
                                ])
                            ),
                            dbc.ModalFooter(dbc.Button("Close", className="ml-auto", id="info-close", n_clicks=0)) 
                        ],
                        id="info-modal", is_open=False, size="xl", centered=True, backdrop=True, scrollable=True # props
                    )
                ], style={'padding':'20px'})  # padding general

    @app.callback(
        Output("reg-rcp45", "children", allow_duplicate=True),
        Output("training-points","children", allow_duplicate= True),
        Output("training-points-legend-div", "children", allow_duplicate= True),
        Input("tabs", "value"),
        prevent_initial_call=True
    )
    def clear_overlay_on_tab_change(tab_value):
        if tab_value != "tab-saltmarsh":
            return [], [], []            # limpiar overlay al salir del tab
        raise PreventUpdate       # no toques nada cuando estás en Saltmarsh


    @app.callback(  # poblar años según área
        Output("year-dropdown","options"),
        Output("year-dropdown","disabled"),
        Input("study-area-dropdown","value")
    )
    def update_year_options(area):  # actualizar años
        if area=="Urdaibai_Estuary": years=[2017,2067,2117]
        elif area=="Bay_of_Santander": years=[2012,2062,2112]
        elif area=="Cadiz_Bay": years=[2023,2073,2123]
        else: return [], True
        return ([{"label":str(y),"value":y} for y in years], False)

    @app.callback(  # centrar/zoom por área
        Output("map", "viewport", allow_duplicate=True),
        Input("study-area-dropdown", "value"),
        prevent_initial_call=True
    )
    def center_and_zoom(area):  # cambiar viewport
        if not area:
            raise PreventUpdate
        mapping = {
            "Urdaibai_Estuary": ([43.364580815052316, -2.67957208131426804], 14),
            "Bay_of_Santander": ([43.43984351219931,  -3.7526739449807447], 15),
            "Cadiz_Bay":        ([36.520874060327226, -6.203490800462997],  15)
        }
        center, zoom = mapping[area]
        return {"center": center, "zoom": zoom}

    @app.callback(  # habilitar Run cuando hay área y año
        Output("run-button","disabled", allow_duplicate=True),
        Input("study-area-dropdown","value"),
        Input("year-dropdown","value"),
        prevent_initial_call=True
    )
    def toggle_run(area, year):  # conmutar estado de Run
        return not (area and year)

    @app.callback(  # pintar overlays para 3 escenarios
        Output("reg-rcp45","children", allow_duplicate=True),
        Output("training-points","children", allow_duplicate=True),
        Output("reset-button", "disabled", allow_duplicate=True),
        Output("study-area-dropdown", "disabled", allow_duplicate=True),
        Output("year-dropdown", "disabled", allow_duplicate=True),
        Output("run-button", "disabled"),
        Output('marsh-results', 'hidden'),
        Output("training-points-legend-div", "children", allow_duplicate=True),
        Input("run-button","n_clicks"),
        State("study-area-dropdown","value"),
        State("year-dropdown","value"),
        prevent_initial_call=True
    )
    def update_map(n, area, year):  # añadir overlays
        if not (n and area and year):
            return [], [], True, False, False, True, True, []
        
        scen = 'regional_rcp45'
        tif_dir = os.path.join(os.getcwd(),"results","saltmarshes",area,scen)  # construir ruta al directorio de TIFs
        matches = glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))  # buscar el TIF del año
        if not matches:  # comprobar que existe el TIF
            raise PreventUpdate  # no actualizar si no hay datos
        m = matches[0]  # tomar el primer TIF disponible
        with rasterio.open(m) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:  # abrir y reproyectar a WGS84 para bounds
            data = vrt.read(1,masked=True)  # leer banda como masked
            import numpy as np  # importar numpy localmente para enmascarado
            data = np.ma.masked_where(data.data==0,data)  # enmascarar clase 0 como nodata por coherencia visual
            b = vrt.bounds  # extraer límites geográficos
        url = f"/raster/{area}/{scen}/{year}.png"  # construir URL del PNG servido por Flask

        overlay = dl.ImageOverlay(
            url=url,
            bounds=[[b.bottom, b.left], [b.top, b.right]],
            opacity=0.95
        )

        # Get the training dataset of the study areas and add it to map:
        if area == "Urdaibai_Estuary":
            points_path = os.path.join(os.getcwd(), "data", "Urdaibai_Estuary", "urdaibai_estuary_training_dataset.parquet")
        elif area == "Bay_of_Santander":
            points_path = os.path.join(os.getcwd(), "data", "Bay_of_Santander", "bay_santander_training_dataset.parquet")
        elif area == "Cadiz_Bay":
            points_path = os.path.join(os.getcwd(), "data", "Cadiz_Bay", "cadiz_bay_training_dataset.parquet")
        else:
            points_path = None

        markers = []

        legend = _build_training_points_legend()

        if points_path and os.path.exists(points_path):
            gdf_points = gpd.read_parquet(points_path)

            # reproyectar a EPSG:4326 (requerido)
            gdf_wgs = gdf_points.to_crs(epsg=4326) if gdf_points.crs is not None else gdf_points.copy()

            # crear marcadores (dl.CircleMarker) por cada punto y asignar color según la clase
            for _, row in gdf_wgs.iterrows():
                geom = row.geometry
                if geom is None:
                    continue
                # obtener lat/lon (WGS84)
                try:
                    lat, lon = float(geom.y), float(geom.x)
                except Exception:
                    try:
                        coords = list(geom.coords)[0]
                        lon, lat = float(coords[0]), float(coords[1])
                    except Exception:
                        continue

                # leer valor de clase (puede ser int o etiqueta str)
                if area == "Urdaibai_Estuary":
                    raw = row.get('Class') if 'Class' in row.index else row.get('class', None)
                else:
                    raw = row.get('class') if 'class' in row.index else row.get('Class', None)

                # normalizar a etiqueta y obtener color
                habitat_label = None
                color = "#000000"
                try:
                    # si es entero -> mapear desde CLASS_INFO
                    if isinstance(raw, (int, float, np.integer)) or (isinstance(raw, (str,)) and raw.isdigit()):
                        idx = int(raw)
                        if idx in CLASS_INFO:
                            habitat_label, color = CLASS_INFO[idx]
                    else:
                        # tratar como texto (p. ej. "Mudflat", "Saltmarsh", ...)
                        habitat_label = str(raw) if raw is not None else "unknown"
                        color = LABEL_TO_COLOR.get(habitat_label, "#000000")
                except Exception:
                    habitat_label = str(raw)

                # crear CircleMarker con fillColor para que se vea el color
                m = dl.CircleMarker(
                    center=[lat, lon],
                    radius=5,
                    color="#000000",        # borde (puede ser igual al relleno)
                    weight=2,
                    fill=True,
                    fillColor= color,
                    fillOpacity=0.9,
                    opacity=1,
                    children=[dl.Tooltip(habitat_label or "")]
                )
                markers.append(m)

        return overlay, markers, False, True, True, True, False, legend  # estados de UI

    @app.callback(  # reset total
        Output("study-area-dropdown", "value", allow_duplicate=True),
        Output("study-area-dropdown", "disabled", allow_duplicate=True),
        Output("year-dropdown", "value", allow_duplicate=True),
        Output("year-dropdown", "disabled", allow_duplicate=True),
        Output("reg-rcp45", "children", allow_duplicate=True),
        Output("saltmarsh-chart", "children", allow_duplicate=True),
        Output('info-button', 'hidden', allow_duplicate=True),
        Output('marsh-results', 'hidden', allow_duplicate=True),
        Output('reset-button', 'disabled', allow_duplicate=True),
        Output('scenario-checklist-div', 'hidden', allow_duplicate=True),
        Output('saltmarsh-legend', 'hidden', allow_duplicate=True),
        Output('scenario-radio', 'value'),
        Output('map', 'viewport'),
        Output("training-points","children"),
        Output("training-points-legend-div", "children"),
        Input("reset-button", "n_clicks"),
        prevent_initial_call=True
    )
    def reset(n):  # limpiar todo
        if n:
            return [None, False, None, True, [], [], True, True, True, True, True, 'reg45', {"center": [40, -3.5], "zoom": 7}, [], []]
        raise PreventUpdate

    @app.callback(  # gráficas con sub-tabs por escenario
        Output("saltmarsh-chart", "children"),
        Output('info-button', "hidden"),
        Output('marsh-results', 'hidden', allow_duplicate=True),
        Output("reset-button", "disabled"),
        Output('scenario-checklist-div', 'hidden'),
        Output('saltmarsh-legend','hidden'),
        Input("run-button", "n_clicks"),
        State("study-area-dropdown", "value"),
        State("year-dropdown", "value"),
        prevent_initial_call=True
    )
    def update_saltmarsh_chart(n, area, year):  # construir gráficas
        if not (n and area and year):
            raise PreventUpdate

        def class_tif(area, scen, year):  # localizar tif de clases
            base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # carpeta base
            hits = glob.glob(os.path.join(base, f"*{year}*.tif")) + glob.glob(os.path.join(base, f"*{year}*.tiff"))  # candidatos
            hits = [p for p in hits if "accretion" not in os.path.basename(p).lower()]  # excluir acreción
            return sorted(hits)[0] if hits else None  # devolver primero o None

        def fig_areas_from_tif(tif_path, y_max_area):
            etiquetas, areas_ha, _ = _areas_por_habitat(tif_path)
            fig = px.bar(
                x=etiquetas, y=areas_ha, title="<b>Habitat Areas (ha)</b>",
                color=etiquetas, color_discrete_map=LABEL_TO_COLOR
            )
            fig.update_traces(
                texttemplate='%{y:.2f}',
                textposition='outside',
                textfont=dict(size=22)
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="<b>Habitat</b>",
                yaxis_title="<b>Area (ha)</b>",
                title_x=0.5,
                title_font_family="Garamond",
                title_font_size=36,
                uniformtext_minsize=10,
                uniformtext_mode='show',
                yaxis_range=[0, y_max_area],
                height=560,
                margin=dict(t=80, r=40, b=120, l=110)  # más aire
            )
            fig.update_xaxes(
                categoryorder='array',
                categoryarray=CATEGORY_ORDER,
                tickfont=dict(size=22),            # tamaño ticks X desde Plotly
                title_font=dict(size=24),          # tamaño título X desde Plotly
                title_standoff=28,                 # separación título–ticks X
                automargin=True
            )
            fig.update_yaxes(
                tickfont=dict(size=22),            # tamaño ticks Y desde Plotly
                title_font=dict(size=24),          # tamaño título Y desde Plotly
                title_standoff=38,                 # separación título–ticks Y
                automargin=True
            )
            return fig


        def fig_acc_from_pair(class_tif_path, y_max_acc):
            acc_tif = _acc_tif_from_class_tif(class_tif_path)
            if not acc_tif:
                return html.Div("No accretion raster found in this scenario folder.",
                                style={"color":"#555","fontStyle":"italic"})
            etiquetas_acc, valores_acc = _accretion_volume_by_class(class_tif_path, acc_tif)
            if not valores_acc:
                return html.Div("No non-zero accumulated accretion found for this scenario.",
                                style={"color":"#555","fontStyle":"italic"})

            fig = px.bar(
                x=etiquetas_acc, y=valores_acc,
                title="<b>Accumulated Accretion (m³) by habitat</b>",
                color=etiquetas_acc, color_discrete_map=LABEL_TO_COLOR
            )
            fig.update_traces(
                texttemplate='%{y:.2f}',
                textposition='outside',
                textfont=dict(size=22)
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="<b>Habitat</b>",
                yaxis_title="<b>Accretion volume (m³/year)</b>",
                title_x=0.5,
                title_font_family="Garamond",
                title_font_size=36,
                uniformtext_minsize=10,
                uniformtext_mode='show',
                yaxis_range=[0, y_max_acc],
                height=560,
                margin=dict(t=80, r=40, b=120, l=110)
            )
            fig.update_xaxes(
                categoryorder='array',
                categoryarray=CATEGORY_ORDER,
                tickfont=dict(size=22),
                title_font=dict(size=24),
                title_standoff=28,
                automargin=True
            )
            fig.update_yaxes(
                tickfont=dict(size=22),
                title_font=dict(size=24),
                title_standoff=38,
                automargin=True
            )
            return dcc.Graph(
                figure=fig,
                config={"modeBarButtonsToRemove": ["zoom2d","pan2d","zoomIn2d","zoomOut2d","lasso2d","resetScale2d"]}
            )



        # Scan all scenarios to find the maximum area and accretion to fix the y-axis of the graphs:
        global_area_max = 0.0
        global_acc_max  = 0.0
        for scen, _ in SCENARIOS:
            t = class_tif(area, scen, year)
            if not t:
                continue
            # áreas
            _, areas_ha, _ = _areas_por_habitat(t)
            if areas_ha:
                global_area_max = max(global_area_max, max(areas_ha))
            # acreción
            acc_t = _acc_tif_from_class_tif(t)
            if acc_t:
                try:
                    _, vals = _accretion_volume_by_class(t, acc_t)
                    if vals:
                        global_acc_max = max(global_acc_max, max(vals))
                except Exception:
                    pass

        # Give a 20% of margin:
        global_area_max = global_area_max * 1.30 if global_area_max else 1.0
        global_acc_max  = global_acc_max  * 1.30 if global_acc_max  else 1.0

        area_tabs_children, acc_tabs_children = [], []  # listas de tabs
        first_value = None  # valor inicial seleccionado

        for scen, scen_label in SCENARIOS:  # recorrer escenarios
            tif_path = class_tif(area, scen, year)  # localizar tif
            if not tif_path:  # si no hay datos
                area_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[html.Div("No class raster found for this scenario/year.", style={"color":"#555","fontStyle":"italic"})]))  # tab vacío
                acc_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[html.Div("No accretion raster found for this scenario/year.", style={"color":"#555","fontStyle":"italic"})]))  # tab vacío
                continue  # siguiente escenario

            fig_areas = fig_areas_from_tif(tif_path, global_area_max)  # construir figura
            area_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[dcc.Graph(figure=fig_areas, config={"modeBarButtonsToRemove": ["zoom2d","pan2d","zoomIn2d","zoomOut2d","lasso2d","resetScale2d"]})], style={"fontSize": "var(--font-md)", "padding": "0.55rem 1rem"}, selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"}))  # tab con figura
            acc_content = fig_acc_from_pair(tif_path, global_acc_max)  # contenido de acreción
            acc_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[acc_content], style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"}, selected_style={"fontSize": "var(--font-md)", "padding": "0.55rem 1rem"}))  # tab de acreción

            if first_value is None:  # fijar tab inicial
                first_value = scen  # seleccionar este

        if first_value is None:  # si ningún escenario tenía datos
            first_value = SCENARIOS[0][0]  # usar primero por defecto

        charts = dcc.Tabs(  # tabs principales
            id="saltmarsh-inner-tabs",  # id de tabs
            className='form-check',
            value="areas",  # seleccionar áreas
            children=[  # dos pestañas principales
                dcc.Tab(  # pestaña de áreas
                    label='Habitat Areas',  # etiqueta
                    value='areas',  # valor
                    children=[dcc.Tabs(id="areas-by-scen", value=first_value, children=area_tabs_children)]  # sub-tabs por escenario
                ),
                dcc.Tab(  # pestaña de acreción
                    label='Accumulated Accretion',  # etiqueta
                    value='accretion',  # valor
                    children=[dcc.Tabs(id="accretion-by-scen", value=first_value, children=acc_tabs_children)]  # sub-tabs por escenario
                )
            ]
        )
        return [charts, False, False, False, False, False]  # devolver UI y mostrar botón info

    @app.callback(  # descarga ZIP por escenario
        Output('saltmarsh-download', 'data'),
        Input('marsh-results', 'n_clicks'),
        State("study-area-dropdown", "value"),
        State("year-dropdown", "value"),
        prevent_initial_call=True
    )
    def download_results(n, area, year):  # construir zip
        if not (n and area and year):
            raise PreventUpdate

        def class_tif(area, scen, year):  # helper localizar tif de clases
            base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # ruta base
            hits = glob.glob(os.path.join(base, f"*{year}*.tif")) + glob.glob(os.path.join(base, f"*{year}*.tiff"))  # candidatos
            hits = [p for p in hits if "accretion" not in os.path.basename(p).lower()]  # excluir acreción
            return sorted(hits)[0] if hits else None  # primero o None

        zip_buf = io.BytesIO()  # buffer del zip
        with ZipFile(zip_buf, 'w') as zf:  # abrir zip
            for scen, _ in SCENARIOS:  # recorrer escenarios
                tif_path = class_tif(area, scen, year)  # localizar tif
                if not tif_path:  # si no existe
                    continue  # saltar
                etiquetas, areas_ha, colores = _areas_por_habitat(tif_path)  # calcular áreas
                titulo = f"Habitat Areas — {area} / {scen} / {year}"  # título
                png_buf = _png_grafico_areas(titulo, etiquetas, areas_ha, colores)  # generar PNG
                zf.writestr(f"{scen}/habitat_areas_{area}_{scen}_{year}.png", png_buf.getvalue())  # añadir PNG
                zf.write(tif_path, arcname=f"{scen}/{os.path.basename(tif_path)}")  # añadir TIF de clases
                acc_tif = _acc_tif_from_class_tif(tif_path)  # localizar accretion
                if acc_tif and os.path.exists(acc_tif):  # si existe
                    try:  # intentar PNG de acreción
                        etiquetas_acc, valores_acc = _accretion_volume_by_class(tif_path, acc_tif)  # calcular volúmenes
                        if valores_acc:  # si hay datos
                            titulo_acc = f"Accumulated Accretion — {area} / {scen} / {year}"  # título
                            acc_png_buf = _png_grafico_accretion(titulo_acc, etiquetas_acc, valores_acc)  # generar PNG
                            zf.writestr(f"{scen}/accumulated_accretion_{area}_{scen}_{year}.png", acc_png_buf.getvalue())  # añadir PNG
                    except Exception:  # silenciar errores de cálculo
                        pass  # continuar
                    zf.write(acc_tif, arcname=f"{scen}/{os.path.basename(acc_tif)}")  # añadir TIF de accretion
        zip_buf.seek(0)  # rebobinar
        return dcc.send_bytes(lambda f: f.write(zip_buf.getvalue()), filename=f"saltmarsh_results_{area}_{year}.zip")  # devolver zip

    @app.callback(  # toggle modal info
        Output("info-modal", "is_open"),
        Input("info-button", "n_clicks"),
        Input("info-close",  "n_clicks"),
        State("info-modal",  "is_open"),
        prevent_initial_call=True
    )
    def toggle_info_modal(open_clicks, close_clicks, is_open):  # alternar modal
        ctx = callback_context  # contexto
        if not ctx.triggered:  # si no hay disparador
            raise PreventUpdate  # no actualizar
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]  # id del disparador
        if trigger in ["info-button", "info-close"]:  # si es abrir/cerrar
            return not is_open  # alternar
        return is_open  # mantener

    
    # Callback para dar funcionalidad al scenario checklist:
    @app.callback(
        Output('reg-rcp45','children', allow_duplicate=True),  # tu contenedor de capas
        Input('scenario-radio','value'),
        State('study-area-dropdown','value'),
        State('year-dropdown','value'),
        prevent_initial_call=True
    )
    def scenario_overlay(selected, area, year):
        if not (area and year and selected):
            raise PreventUpdate
        scen_map = {'reg45':'regional_rcp45','reg85':'regional_rcp85','glo45':'global_rcp45'}
        scen = scen_map[selected]
        base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)
        matches = sorted(glob.glob(os.path.join(base, f"*{year}*.tif")))
        if not matches:
            return []
        with rasterio.open(matches[0]) as src, WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.nearest) as vrt:
            b = vrt.bounds
        url = f"/raster/{area}/{scen}/{year}.png?ts={int(time.time())}"
        return [dl.ImageOverlay(id=f"overlay-{scen}", url=url,
                                bounds=[[b.bottom,b.left],[b.top,b.right]], opacity=1)]
    
    # Callback para cambiar los link del footer y el texto si es el caso:
    @app.callback(
        Output("method-link", "children"),
        Output("method-link", "href"),
        Output("code-link", "children"),
        Output("code-link", "href"),
        Input("tabs", "value"),
    )
    def update_footer_links_full(tab):
        labels = {
            "tab-saltmarsh":  ("Access the methodology", "Access the code"),
            "tab-physical":   ("Access the methodology", "Access the code"),
            "tab-fishstock":  ("Fish Stocks docs", "Fish Stocks code"),
            "tab-management": ("Management docs", "Management code"),
        }
        urls = {
            "tab-saltmarsh":  ("https://doi.org/10.1016/j.scitotenv.2024.178164",
                            "https://github.com/begidazu/PhD_Web_App/tree/main/saltmarsh"),
            "tab-physical":   ("https://docs.google.com/document/d/1qBrr96Hek-HVC-K4_4n9cyR9cEJ_d24o/edit#heading=h.i7jku579q3oc",
                            "https://github.com/begidazu/PhD_Web_App/blob/physical_accounts/app/models/opsa.py"),
            "tab-fishstock":  (),
            "tab-management": (),
        }
        m_text, c_text = labels.get(tab, labels["tab-saltmarsh"])
        m_href, c_href = urls.get(tab, urls["tab-saltmarsh"])
        method_children = [html.Span('📄', className="me-1 footer-icon"), m_text]
        code_children   = [html.Img(src="/assets/logos/github-mark.png", className="me-1 footer-icon"), c_text]
        return method_children, m_href, code_children, c_href
    

    # Callback para mostrar el modal al iniciar la app: 
    @app.callback(
        Output("welcome-modal", "is_open"),
        Output("welcome-store", "data"),
        Input("welcome-close", "n_clicks"),
        State("welcome-dont-show", "value"),
        State("welcome-store", "data"),
        prevent_initial_call=False
    )
    def control_welcome_modal(n_close, dont_show, store):
        # 1ª carga: si no hay estado en la sesión, mostramos el modal
        if store is None:
            # Si aún no se ha pulsado cerrar, lo mostramos
            if not n_close:
                return True, None
        # Si se pulsó cerrar, persistimos la preferencia
        if n_close:
            return False, {"dismissed": bool(dont_show)}
        # Si ya había estado en sesión:
        if isinstance(store, dict) and store.get("dismissed", False):
            return False, store  # no mostrar más en esta sesión si marcó la casilla
        return True, store       # de lo contrario, mostrar


    # Callback to open the welcome modal when they click the ? button:

    @app.callback(
        Output("welcome-modal", "is_open", allow_duplicate=True),
        Input("help-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def welcome_callback_button(click):
        if click:
            return True
