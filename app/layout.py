from dash import html, dcc  # importar componentes básicos de Dash
import dash_leaflet as dl  # importar integración Leaflet
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
                                                position='topleft',  # ubicación del control
                                                draw={  # herramientas activas
                                                    'polygon': True,  # permitir polígonos
                                                    'polyline': False,  # desactivar polilíneas
                                                    'rectangle': False,  # desactivar rectángulo
                                                    'circle': False,  # desactivar círculo
                                                    'marker': False  # desactivar marcador
                                                },
                                                edit={'remove': True}  # permitir borrar
                                            )
                                        ]
                                    ),
                                    dl.FeatureGroup(id='opsa-layer', children=[]),
                                     # --- Leyenda OPSA (contenedor, el contenido lo rellenan callbacks) ---
                                    html.Div(  # contenedor de la leyenda flotante
                                        id='opsa-legend',  # id para actualizar desde callbacks
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
                                    html.Div(
                                        [
                                            dcc.Loading(type='circle',  parent_style={"position": "relative", "z-index": "100", "width": "100%", "height": "100%"}), 
                                            dl.FeatureGroup(id='reg-rcp45', children=[])
                                        ]
                                    )
                                ]
                            )
                        ]
                    ),
                    dbc.Col(  # columna de la barra lateral
                        lg=4, md=12, sm=12,  # tamaños por breakpoint
                        className="d-flex flex-column bg-light",  # fondo claro
                        children=[  # hijos de la barra lateral
                            dcc.Tabs(  # tabs principales
                                id='tabs',  # id de tabs
                                value='tab-saltmarsh',  # tab seleccionada por defecto
                                className="tabs mb-2",  # clases CSS
                                children=[  # pestañas
                                    dcc.Tab(label='Saltmarsh evolution',  value='tab-saltmarsh'),  # tab 1
                                    dcc.Tab(label='Fish Stocks',          value='tab-fishstock'),  # tab 2
                                    dcc.Tab(label='Physical Accounts',    value='tab-physical'),  # tab 3
                                    dcc.Tab(label='Management Scenarios', value='tab-management'),  # tab 4
                                ],
                                style={'fontWeight': 'bold'}  # estilo de fuente
                            ),
                            html.Div(  # contenedor del contenido de la pestaña
                                id='tab-content',  # id del contenedor
                                className="flex-grow-1 overflow-auto p-2 bg-white rounded shadow-sm"  # estilos
                            ),
                            html.Div(  # pie con enlaces
                                className="p-2 mt-auto",  # padding y empujar abajo
                                children=[  # enlaces
                                    # --- enlace a paper (añado 'footer-link' y mantengo el emoji con 'footer-icon') ---
                                    html.A( # enlace a paper
                                        [html.Span('📄', className="me-1 footer-icon"), "Access the methodology"],  # icono + texto
                                        id='method-link',
                                        href='https://doi.org/10.1016/j.scitotenv.2024.178164',  # url del paper
                                        target='_blank',  # abrir en nueva pestaña
                                        className="d-flex align-items-center text-decoration-none text-dark mb-1 footer-link"  # añado 'footer-link' para tamaño
                                    ),

                                    # --- enlace a GitHub (mismo patrón: 'footer-icon' y 'footer-link') ---
                                    html.A(  # enlace a repo
                                        [html.Img(src='/assets/logos/github-mark.png', className="me-1 footer-icon"), "Access the code"],  # icono + texto
                                        id='code-link',
                                        href='https://github.com/begidazu/PhD_Web_App',  # url del repo
                                        target='_blank',  # abrir en nueva pestaña
                                        className="d-flex align-items-center text-decoration-none text-dark footer-link"  # añado 'footer-link' para tamaño
                                    )
                                ]
                            )
                        ]
                    ),

                    # almacén de sesión para recordar si se ocultó
                    dcc.Store(id="welcome-store", storage_type="session"),

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

