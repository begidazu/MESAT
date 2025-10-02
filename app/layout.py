from dash import html, dcc  # importar componentes básicos de Dash
import dash_leaflet as dl  # importar integración Leaflet
from dash_extensions.javascript import assign
import dash_bootstrap_components as dbc  # importar Bootstrap para layout

# Layout completamente flexible y responsive usando utilidades de Bootstrap
def create_layout():  # definir función que construye el layout
    return html.Div(  # contenedor raíz
        className="d-flex flex-column vh-100 p-0",  # hacer columna a pantalla completa
        children=[  # hijos del contenedor raíz
            dbc.Row(  # fila principal
                className="flex-grow-1 g-0",  # ocupar todo y sin gutters
                children=[  # hijos de la fila
                    dbc.Col(  # columna del mapa
                        lg=8, md=12, sm=12,  # tamaños por breakpoint
                        className="d-flex flex-column p-0",  # sin padding interno
                        children=[  # hijos de la columna de mapa
                            dl.Map(  # crear mapa Leaflet
                                id='map',  # id del mapa
                                center=[40, -3.5],  # centro por defecto
                                zoom=7,  # zoom por defecto
                                style={'width': '100%', 'height': '100%'},  # ocupar 100%
                                children=[  # hijos del mapa
                                    dl.TileLayer(),  # capa base OSM
                                    dl.FeatureGroup(  # grupo de dibujo
                                        id='draw-layer',  # id del grupo de dibujo
                                        children=[  # hijos del grupo de dibujo
                                            dl.EditControl(  # control de edición
                                                id='edit-control',  # id del control
                                                draw={"polyline": False, "rectangle": False, "circle": False, "circlemarker": False, "marker": False, "polygon": True},
                                                edit={"edit": True, "remove": True}
                                            )
                                        ]
                                    ),
                                    # Layers where we store the raster tiles for the saltmarsh model
                                    dl.FeatureGroup(id='reg-rcp45', children=[]),
                                    # Layer where we store the EUNIS habitat polygons:
                                    dl.FeatureGroup(id='opsa-layer', children=[]),
                                     # OPSA legend:
                                    html.Div(  # contenedor de la leyenda flotante
                                        id='opsa-legend-div',  # id para actualizar desde callbacks
                                        style={  # estilos para posicionarla sobre el mapa
                                            'position': 'absolute',  # posición absoluta dentro del mapa
                                            'bottom': '10px',  # distancia al borde inferior
                                            'left': '10px',  # distancia al borde izquierdo
                                            'zIndex': 1000,  # por encima del mapa
                                            'background': 'rgba(255,255,255,0.92)',  # fondo semitransparente
                                            'border': '1px solid #ccc',  # borde sutil
                                            'borderRadius': '8px',  # esquinas redondeadas
                                            'padding': '8px 10px',  # espaciado interno
                                            'boxShadow': '0 2px 6px rgba(0,0,0,0.15)',  # sombra suave
                                            'fontSize': '12px'  # tamaño de fuente
                                        },
                                        children=[]  # vacío al inicio; se completa al ejecutar OPSA
                                    ),

                                    
                                    # Layers where we store the management polygons
                                    dl.FeatureGroup(id="mgmt-wind", children=[]),
                                    dl.FeatureGroup(id="mgmt-aquaculture", children=[]),
                                    dl.FeatureGroup(id="mgmt-vessel", children=[]),
                                    dl.FeatureGroup(id="mgmt-defence", children=[]),

                                    # Layers where we store the uploaded files:
                                    dl.FeatureGroup(id="mgmt-wind-upload", children=[]),  # capa para los datos subidos (Wind)
                                    dl.FeatureGroup(id="mgmt-aquaculture-upload", children=[]),  # capa para los datos subidos (Aquaculture)
                                    dl.FeatureGroup(id="mgmt-vessel-upload", children=[]),# capa para los datos subidos (Vessel Routes)
                                    dl.FeatureGroup(id="mgmt-defence-upload", children=[])# capa para los datos subidos (Defence)

                                ]
                            ),

                        ]
                    ),
                    dbc.Col(  # columna de la barra lateral
                        lg=4, md=12, sm=12,  # tamaños por breakpoint
                        className="d-flex flex-column bg-light",  # fondo claro
                        children=[  # hijos de la barra lateral
                            dcc.Tabs(  # tabs principales
                                id='tabs',  # id de tabs
                                value='tab-management',  # tab seleccionada por defecto
                                className="tabs mb-2",  # clases CSS
                                children=[  # pestañas
                                    dcc.Tab(label='Management Scenarios', value='tab-management'),  # tab 1
                                    dcc.Tab(label='Saltmarsh evolution',  value='tab-saltmarsh'),  # tab 2
                                    dcc.Tab(label='Physical Accounts',    value='tab-physical'),  # tab 3
                                    dcc.Tab(label='EVA-MPAEU Overscale', value='tab-eva-overscale'),  # tab 4
                                    dcc.Tab(label='Fish Stocks', value='tab-fishstock'),  # tab 5 
                                    
                                ],
                                style={'fontWeight': 'bold'}  # estilo de fuente
                            ),
                            html.Div(  # contenedor del contenido de la pestaña
                                id='tab-content',  # id del contenedor
                                className="flex-grow-1 overflow-auto p-2 bg-white rounded shadow-sm"  # estilos
                            ),
                            html.Div(
                                className="p-2 mt-auto d-flex justify-content-between align-items-stretch",
                                style={"minHeight": "56px"},  # altura mínima del footer
                                children=[
                                    # bloque de enlaces a la izquierda (en columna)
                                    html.Div(
                                        [
                                            html.A(
                                                [html.Span('📄', className="me-1 footer-icon"), "Access the methodology"],
                                                id='method-link',
                                                href='https://doi.org/10.1016/j.scitotenv.2024.178164',
                                                target='_blank',
                                                className="d-flex align-items-center text-decoration-none text-dark mb-1 footer-link"
                                            ),
                                            html.A(
                                                [html.Img(src='/assets/logos/github-mark.png', className="me-1 footer-icon"), "Access the code"],
                                                id='code-link',
                                                href='https://github.com/begidazu/PhD_Web_App',
                                                target='_blank',
                                                className="d-flex align-items-center text-decoration-none text-dark footer-link"
                                            ),
                                        ],
                                        className="d-flex flex-column",
                                    ),

                                    # botón de ayuda a la derecha (mismo alto que el bloque de la izquierda)
                                    dbc.Button(
                                        "?",
                                        id="help-btn",
                                        n_clicks=0,
                                        outline=True,
                                        color='primary',
                                        className="fw-bold d-flex justify-content-center align-items-center",
                                        style={
                                            "height": "100%",         # ocupa todo el alto del footer
                                            "aspectRatio": "1 / 1",   # cuadrado perfecto
                                            "padding": 0,
                                            "lineHeight": "1",
                                            'borderRadius': "50%",
                                            "fontSize": "2rem"
                                        },
                                    ),
                                    # tooltip (hover info for help-btn)
                                    dbc.Tooltip(
                                        "Open Welcome modal",  # el texto del hover
                                        target="help-btn",  # id del botón al que se engancha
                                        placement="top",   # posición del tooltip (top, bottom, left, right)
                                    )
                                ],
                            )
                        ]
                    ),

                    # almacén de sesión: recargar la pestaña no pierde la sesión, eliminarla y volver a abrir la app si. La sesion es un ID que se guarda en el navegador y se usa para recordad los uploads de cada sesion
                    dcc.Store(id="welcome-store", storage_type="session"),
                    dcc.Store(id="session-id", storage_type="session"),
                    # almacen para guardar los poligonos dibujados por los susuarios sobre actividades economicas
                    dcc.Store(id="draw-meta", data={"layer": "wind", "color": "#f59e0b"}),
                    dcc.Store(id="draw-len", data=0),
                    # almacen para guardar los ficheros subidos por actividad economica
                    dcc.Store(id="wind-file-store"),                           # store para Wind Farm
                    dcc.Store(id="aquaculture-file-store"),                    # store para Aquaculture
                    dcc.Store(id="vessel-file-store"),                         # store para Vessel Route
                    dcc.Store(id="defence-file-store"),                        # store para Defence


                    # modal de bienvenida
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Welcome to the MSP GIS App")),
                            dbc.ModalBody(
                                html.Div(
                                    [
                                        html.P("Here a quick summary of how to use the app:"),
                                        html.Ul([
                                            html.Li("AAAAA."),
                                            html.Li("BBBBB"),
                                            html.Li("CCCCC"),
                                        ]),
                                        html.Div(
                                            dbc.Checkbox(
                                                id="welcome-dont-show",
                                                label="Don't show this again",
                                                value=False,
                                                className="mt-2"
                                            )
                                        ),
                                    ]
                                )
                            ),
                            dbc.ModalFooter(
                                dbc.Button("Continue", id="welcome-close", n_clicks=0, className="ms-auto")
                            ),
                        ],
                        id="welcome-modal",
                        is_open=True,          # ← se abre al cargar (el callback decidirá si mostrar o no)
                        centered=True,
                        scrollable=True,
                        backdrop="static",     # ← evita cerrar clicando fuera
                        keyboard=False,        # ← evita cerrar con ESC
                        size="xl",             # ← base; el ancho real lo controlamos en CSS
                    ),
                ]
            )
        ]
    )

