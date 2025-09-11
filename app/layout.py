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
                                    # Economic activities legend:
                                    html.Div(
                                        id='mgmt-legend-div',
                                        style={
                                            'position': 'absolute',
                                            'bottom': '10px',
                                            'left': '10px',
                                            'zIndex': 1000, 
                                            'background': 'rgba(255,255,255,0.92)',  
                                            'border': '1px solid #ccc', 
                                            'borderRadius': '8px',  
                                            'padding': '8px 10px',  
                                            'boxShadow': '0 2px 6px rgba(0,0,0,0.15)',  
                                        },
                                        className='legend',
                                        hidden=True,
                                        children=[
                                            html.Div("Condition", style={'fontWeight':'bold','marginBottom':'6px'}),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={'width':'14px','height':'14px','background':"#f39c12",'border':'1px solid #888'}
                                                    ),
                                                    html.Span("Wind Farms")
                                                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '4px'}
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={'width':'14px','height':'14px','background':"#18BC9C",'border':'1px solid #888'}
                                                    ),
                                                    html.Span("Aquaculture")
                                                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '4px'}
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={'width':'14px','height':'14px','background':"#3498DB",'border':'1px solid #888'}
                                                    ),
                                                    html.Span("New Vessel Routes")
                                                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '4px'}
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={'width':'14px','height':'14px','background':"#e74c3c",'border':'1px solid #888'}
                                                    ),
                                                    html.Span("Defence")
                                                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '4px'}
                                            )
                                        ]  
                                    ),

                                    
                                    # Layers where we store the management polygons
                                    dl.FeatureGroup(id="mgmt-wind", children=[]),
                                    dl.FeatureGroup(id="mgmt-aquaculture", children=[]),
                                    dl.FeatureGroup(id="mgmt-vessel", children=[]),
                                    dl.FeatureGroup(id="mgmt-defence", children=[]),

                                    # Layers where we store the uploaded files:
                                    dl.FeatureGroup(id="mgmt-wind-upload", children=[]),  # capa para los datos subidos (Wind)
                                    dl.FeatureGroup(id="mgmt-aquaculture-upload", children=[]),  # capa para los datos subidos (Aquaculture)
                                    dl.FeatureGroup(id="mgmt-vessel-upload", children=[]), # capa para los datos subidos (Vessel Routes)
                                    dl.FeatureGroup(id="mgmt-defence-upload", children=[]), # capa para los datos subidos (Defence)
















                                    # LayersControl to add the information useful to delimit economic activity areas. THIS IS IN TEST MODE:
                                        # Botón con el icono (bajo el EditControl)
                                    # html.Button(
                                    #     id="layers-btn",
                                    #     className="btn btn-outline-primary",   # estilos abajo
                                    #     n_clicks=0,
                                    #     title="Layers",
                                    #     children=html.Img(src="/assets/logos/layers.png", className="layers-icon"),
                                    # ),

                                    dbc.Button(
                                        html.I(className="bi bi-layers", style={"fontSize": "1.6rem", "lineHeight": 1}),
                                        id="layers-btn",
                                        color="light",
                                        n_clicks=0,
                                        disabled = True,
                                        className="shadow-sm border rounded-1 position-absolute d-flex align-items-center justify-content-center",
                                        style={"left": "10px", "top": "78px", "zIndex": 1000, "width": "46px", "height": "46px"},
                                    ),
                                    # html.Div(
                                    #     id="layer-menu",
                                    #     className="layers-panel",
                                    #     children=[
                                    #         html.Div("Layers", className="lm-header"),   # título siempre visible
                                    #         html.Div(                                   # cuerpo que se despliega al hover
                                    #             [
                                    #                 html.Div("Human activities", className="lm-group-title"),
                                    #                 dcc.Checklist(
                                    #                     id="chk-human",
                                    #                     options=[
                                    #                         {"label": "HA 1", "value": "mgmt-ha-1"},
                                    #                         {"label": "HA 2", "value": "mgmt-ha-2"},
                                    #                     ],
                                    #                     value=[],
                                    #                     className="lm-checklist",
                                    #                 ),
                                    #                 html.Div("Fishery", className="lm-group-title"),
                                    #                 dcc.Checklist(
                                    #                     id="chk-fish",
                                    #                     options=[
                                    #                         {"label": "Effort",   "value": "mgmt-fish-effort"},
                                    #                         {"label": "Closures", "value": "mgmt-fish-closures"},
                                    #                     ],
                                    #                     value=[],
                                    #                     className="lm-checklist",
                                    #                 ),
                                    #             ],
                                    #             className="lm-body",
                                    #         ),
                                    #     ],
                                    # )
                                    html.Div(
                                        id="layer-menu",
                                        className="card shadow-sm position-absolute collapse",
                                        style={"left":"10px","top":"128px","zIndex":1000,"minWidth":"260px"},
                                        children=[
                                            html.Div("Additional information", className="card-header py-2 fw-bold text-uppercase"),
                                            dbc.Accordion(  # crear contenedor acordeón para grupos plegables
                                                id="layers-accordion",  # id del acordeón para CSS/depuración
                                                always_open=True,  # permitir varios grupos abiertos a la vez
                                                start_collapsed=True,  # iniciar todos los grupos cerrados
                                                className="layers-accordion",  # clase para estilos finos
                                                children=[  # lista de grupos del acordeón
                                                    dbc.AccordionItem(  # primer grupo: Human activities
                                                        title="Human activities",  # texto de cabecera con flecha a la derecha
                                                        class_name="layers-acc-item",  # clase para márgenes del item
                                                        children=[
                                                            dbc.Accordion(
                                                                start_collapsed = True,
                                                                always_open = True,
                                                                children = [
                                                                    dbc.AccordionItem(
                                                                        title="Wind Farms",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-wind-farm-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Wind Farm Points",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/8201070b-4b0b-4d54-8910-abcea5dce57f",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-wf-points"  # valor del switch
                                                                                    },
                                                                                    {"label": html.Span("Wind Farm Polygons", style={"fontSize": "0.9rem"}), "value": "mgmt-wf-polygons"},
                                                                                    {"label": html.Span("Technical Suitability", style={"fontSize": "0.9rem"}), "value": "mgmt-wf-tech-suit"}
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    )
                                                                ]
                                                            )
                                                            
                                                        ]
                                                        # children=[  # contenido cuando el grupo está desplegado
                                                        #     dbc.Checklist(  # switches del grupo Human
                                                        #         id="chk-human",  # mantener id original para callbacks existentes
                                                        #         options=[  # opciones que encienden capas
                                                        #             {"label": html.Span("HA 1", style={"fontSize": "0.9rem"}), "value": "mgmt-ha-1"},  # etiqueta + valor
                                                        #             {"label": html.Span("HA 2", style={"fontSize": "0.9rem"}), "value": "mgmt-ha-2"},  # etiqueta + valor
                                                        #         ],
                                                        #         value=[],  # sin selección por defecto
                                                        #         switch=True,  # estilo tipo interruptor
                                                        #         className="mb-1",  # pequeño margen inferior
                                                        #     )
                                                        # ],
                                                    ),
                                                    dbc.AccordionItem(  # segundo grupo: Fishery
                                                        title="Fishery",  # cabecera con flecha
                                                        class_name="layers-acc-item",  # clase para márgenes del item
                                                        children=[  # contenido al abrir el grupo
                                                            dbc.Checklist(  # switches del grupo Fishery
                                                                id="chk-fish",  # mantener id original para callbacks existentes
                                                                options=[  # opciones de pesca
                                                                    {"label": html.Span("Effort", style={"fontSize": "0.9rem"}), "value": "mgmt-fish-effort"},  # esfuerzo pesquero
                                                                    {"label": html.Span("Closures", style={"fontSize": "0.9rem"}), "value": "mgmt-fish-closures"},  # cierres
                                                                ],
                                                                value=[],  # sin selección por defecto
                                                                switch=True,  # estilo interruptor
                                                            )
                                                        ],
                                                    ),
                                                ],
                                            )
                                        ],
                                    )













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

