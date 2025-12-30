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
                                zoomControl = False,
                                style={'width': '100%', 'height': '100%'},  # ocupar 100%
                                children=[  # hijos del mapa
                                    dl.TileLayer(),  # capa base OSM
                                    dl.ZoomControl(position="topright"),
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
                                    # Layers where we store the training points for the saltmarsh model
                                    dl.FeatureGroup(id='training-points', children=[]),
                                    html.Div(  # contenedor de la leyenda flotante
                                        id='training-points-legend-div',  # id para actualizar desde callbacks
                                        style={  # estilos para posicionarla sobre el mapa
                                            'position': 'absolute',  # posición absoluta dentro del mapa
                                            'bottom': '10px',  # distancia al borde inferior
                                            'left': '10px',  # distancia al borde izquierdo
                                            'zIndex': 1001,  # por encima del mapa
                                            'background': 'rgba(255,255,255,0.92)',  # fondo semitransparente
                                            'border': '1px solid #ccc',  # borde sutil
                                            'borderRadius': '8px',  # esquinas redondeadas
                                            'padding': '8px 10px',  # espaciado interno
                                            'boxShadow': '0 2px 6px rgba(0,0,0,0.15)',  # sombra suave
                                            'fontSize': '12px'  # tamaño de fuente
                                        },
                                        children=[]  # vacío al inicio; se completa al ejecutar OPSA
                                    ),

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
                                            html.Div("Activities", style={'fontWeight':'bold','marginBottom':'6px'}),
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
                                    dl.FeatureGroup(id="mgmt-vessel-upload", children=[]),# capa para los datos subidos (Vessel Routes)
                                    dl.FeatureGroup(id="mgmt-defence-upload", children=[]), # capa para los datos subidos (Defence)

                                    # Layers where we store the uploaded files of eva-overscale, the drew study area and the results
                                    dl.FeatureGroup(id="eva-overscale-draw", children=[]),
                                    dl.FeatureGroup(id="eva-overscale-upload", children=[]),

                                    # Div to Store EVA Overscale Accordion:
                                    html.Div(
                                        id="eva-results-accordion-container",
                                        className="card shadow-sm position-absolute",
                                        style={"left":"10px","top":"10px","zIndex":1000,"minWidth":"260px"},
                                    ),
                                    html.Div(  # contenedor de la leyenda flotante
                                        id='eva-overscale-legend-div',  # id para actualizar desde callbacks
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
                                    # Layers of the Accordion:
                                    dl.FeatureGroup(id="eva-aq-layer", children=[]),

                                    # Layers where we store the additional info for activities:
                                    dl.LayerGroup(id="dynamic-overlays"),

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
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Wind Farm Polygons",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/8201070b-4b0b-4d54-8910-abcea5dce57f",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-wf-polygons"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Technical Suitability",  # texto clicable
                                                                                                    href="",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-wf-techsuit"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Aquaculture",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-aquaculture-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Finfish Production",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/03c35b79-808f-4168-9d30-2de44a55a6f4",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-aquaculture-finfish"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Shellfish Production",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/aa0d2b45-49c4-4b42-86bb-8971a3c2d2cc",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-aquaculture-shellfish"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Vessel Density",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-vessel-density-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "All type annual average (2017-2023)",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/0f2f3ff1-30ef-49e1-96e7-8ca78d58a07c",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-vessel-density-alltype-annualavg"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Fishing Intensity",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-fishing-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Beam trawls",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d57fbdea-489e-4e11-9ff1-f0f706cfe783",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-fishing-beam-trawls"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Bottom otter trawls",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d57fbdea-489e-4e11-9ff1-f0f706cfe783",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-fishing-bottom-otter"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Bottom seines",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d57fbdea-489e-4e11-9ff1-f0f706cfe783",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-fishing-bottom-seines"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Dredges",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d57fbdea-489e-4e11-9ff1-f0f706cfe783",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-fishing-dredges"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Pelagic trawls and seines",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d57fbdea-489e-4e11-9ff1-f0f706cfe783",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-fishing-pelagic"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Static gears",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d57fbdea-489e-4e11-9ff1-f0f706cfe783",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-fishing-static-gears"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Military Areas",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-military-areas-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Military Areas (polygons)",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/579e4a3b-95e4-48c6-8352-914ebae0ae1d",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-military-areas-polygons"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Protected Areas",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-protected-areas-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Natura 2000 sites",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/ac911c34-1692-4642-a031-87bcb5822158",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-protected-areas-natura2000"  # valor del switch
                                                                                    },
                                                                                                                                                                        {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "World Database on Protected Areas",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/f727edd7-87b8-4b02-b173-14ca13025f6f",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-protected-areas-world-database"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Ports",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-main-ports-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Main Ports (vessel traffic by tonnage)",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/379d0425-8924-4a41-a088-1a002d2ea748",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-main-ports"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Waste Disposal",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-waste-disposal-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Discharge Points",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/0bd23b5e-b288-4273-b8b7-d073538ada52",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-waste-disposal-discharge"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Waste at Ports",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/849e0a11-b5ae-4094-82ec-9e8ae0cedb09",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-waste-disposal-waste"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Dumped Munitions (points)",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/661aa259-8ea9-49ae-a39d-49685057b013",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-waste-disposal-dumped-munitions-points"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Extraction",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-extraction-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Aggregate Extraction Areas",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/fde45abd-7bf3-4f05-869c-d1ce77f4ac63",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-extraction-aggregate-extraction"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Dredging",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-dredging-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Dredging",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/d3e86612-35a7-4c0f-a995-245062fd2792",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-dredging-dredging"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Oil & Gas",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-oil-gas-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Offshore Installations",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/ddbe3597-4e3f-4e74-8d31-947c4efef2e9",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-oil-gas-offshore-installations"  # valor del switch
                                                                                    }
                                                                                ],
                                                                                value=[],
                                                                                switch=True
                                                                            )
                                                                        ]
                                                                    ),
                                                                    dbc.AccordionItem(
                                                                        title="Cables",
                                                                        children=[
                                                                            dbc.Checklist(
                                                                                id="mgmt-cables-info",
                                                                                options=[
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Power Cables",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/41b339f8-b29c-4550-b787-3d68f08fdbcc",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-cables-power-cables"  # valor del switch
                                                                                    },
                                                                                    {
                                                                                        "label": html.Span(  # contenedor del label
                                                                                            [  # hijos del label
                                                                                                html.A(  # hacer el texto un enlace real
                                                                                                    "Telecomunication Cables",  # texto clicable
                                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/39ebe289-410b-4a5d-88a4-51bfcde538de",  # url destino
                                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                                    rel="noopener noreferrer"
                                                                                                )
                                                                                            ],
                                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                                        ),
                                                                                        "value": "mgmt-cables-telecomunication-cables"  # valor del switch
                                                                                    }
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
                                                        title="Geology",  # cabecera con flecha
                                                        class_name="layers-acc-item",  # clase para márgenes del item
                                                        children=[
                                                            dbc.Checklist(  # switches del grupo Fishery
                                                                id="mgmt-geology-info",  # mantener id original para callbacks existentes
                                                                options=[  # opciones de pesca
                                                                    {
                                                                        "label": html.Span(  # contenedor del label
                                                                            [  # hijos del label
                                                                                html.A(  # hacer el texto un enlace real
                                                                                    "Seabed Substrate (multiscale - folk 7)",  # texto clicable
                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/6eaf4c6bf28815e973b9c60aab5734e3ef9cd9c4",  # url destino
                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                    rel="noopener noreferrer"
                                                                                )
                                                                            ],
                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                        ),
                                                                        "value": "mgmt-geology-seabed-substrate"  # valor del switch
                                                                    },
                                                                    {
                                                                        "label": html.Span(  # contenedor del label
                                                                            [  # hijos del label
                                                                                html.A(  # hacer el texto un enlace real
                                                                                    "Sedimentation Rates (cm/year)",  # texto clicable
                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/cd0ae8d1ea0ed39546c9ba66b1bf5d3fefda2c7b",  # url destino
                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                    rel="noopener noreferrer"
                                                                                )
                                                                            ],
                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                        ),
                                                                        "value": "mgmt-geology-sedimentation-rates"  # valor del switch
                                                                    }
                                                                    # {
                                                                    #     "label": html.Span(  # contenedor del label
                                                                    #         [  # hijos del label
                                                                    #             html.A(  # hacer el texto un enlace real
                                                                    #                 "Marine Critical Minerals",  # texto clicable
                                                                    #                 href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/67862a1e-6a18-4a0f-84c8-5b480a010855",  # url destino
                                                                    #                 target="_blank",  # abrir en nueva pestaña
                                                                    #                 rel="noopener noreferrer"
                                                                    #             )
                                                                    #         ],
                                                                    #         style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                    #     ),
                                                                    #     "value": "mgmt-geology-critical-minerals"  # valor del switch
                                                                    # },
                                                                    #                                                                     {
                                                                    #     "label": html.Span(  # contenedor del label
                                                                    #         [  # hijos del label
                                                                    #             html.A(  # hacer el texto un enlace real
                                                                    #                 "Marine Hydrocarbons and Hydrates",  # texto clicable
                                                                    #                 href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/67862ceb-c4a0-45df-a3c1-5b4c0a010855",  # url destino
                                                                    #                 target="_blank",  # abrir en nueva pestaña
                                                                    #                 rel="noopener noreferrer"
                                                                    #             )
                                                                    #         ],
                                                                    #         style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                    #     ),
                                                                    #     "value": "mgmt-geology-hydrocarbons-hydrates"  # valor del switch
                                                                    # }
                                                                ],
                                                                value=[],  # sin selección por defecto
                                                                switch=True,  # estilo interruptor
                                                            )
                                                        ]
                                                    ),
                                                    dbc.AccordionItem(  # segundo grupo: Fishery
                                                        title="Geography",  # cabecera con flecha
                                                        class_name="layers-acc-item",  # clase para márgenes del item
                                                        children=[
                                                            dbc.Checklist(  # switches del grupo Fishery
                                                                id="mgmt-geography-info",  # mantener id original para callbacks existentes
                                                                options=[  # opciones de pesca
                                                                    {
                                                                        "label": html.Span(  # contenedor del label
                                                                            [  # hijos del label
                                                                                html.A(  # hacer el texto un enlace real
                                                                                    "Coastline - Mean High Water",  # texto clicable
                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/be8828f0-9390-4e5d-8f30-6831463d4d4b",  # url destino
                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                    rel="noopener noreferrer"
                                                                                )
                                                                            ],
                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                        ),
                                                                        "value": "mgmt-geography-coastline"  # valor del switch
                                                                    },
                                                                    {
                                                                        "label": html.Span(  # contenedor del label
                                                                            [  # hijos del label
                                                                                html.A(  # hacer el texto un enlace real
                                                                                    "Bathymetry",  # texto clicable
                                                                                    href="https://emodnet.ec.europa.eu/geonetwork/srv/eng/catalog.search#/metadata/cf51df64-56f9-4a99-b1aa-36b8d7b743a1",  # url destino
                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                    rel="noopener noreferrer"
                                                                                )
                                                                            ],
                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                        ),
                                                                        "value": "mgmt-geography-bathymetry"  # valor del switch
                                                                    }
                                                                ],
                                                                value=[],  # sin selección por defecto
                                                                switch=True,  # estilo interruptor
                                                            )
                                                        ]
                                                    ),
                                                    dbc.AccordionItem(  # segundo grupo: Fishery
                                                        title="Ecology",  # cabecera con flecha
                                                        class_name="layers-acc-item",  # clase para márgenes del item
                                                        children=[
                                                            dbc.Checklist(  # switches del grupo Fishery
                                                                id="mgmt-ecology-info",  # mantener id original para callbacks existentes
                                                                options=[  # opciones de pesca
                                                                    {
                                                                        "label": html.Span(  # contenedor del label
                                                                            [  # hijos del label
                                                                                html.A(  # hacer el texto un enlace real
                                                                                    "Species richness",  # texto clicable
                                                                                    href="",  # url destino
                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                    rel="noopener noreferrer"
                                                                                )
                                                                            ],
                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                        ),
                                                                        "value": "mgmt-ecology-speciess-richness"  # valor del switch
                                                                    },
                                                                    {
                                                                        "label": html.Span(  # contenedor del label
                                                                            [  # hijos del label
                                                                                html.A(  # hacer el texto un enlace real
                                                                                    "IUCN Red List/Endangered Species number",  # texto clicable
                                                                                    href="",  # url destino
                                                                                    target="_blank",  # abrir en nueva pestaña
                                                                                    rel="noopener noreferrer"
                                                                                )
                                                                            ],
                                                                            style={"fontSize": "0.9rem"}  # tamaño del texto
                                                                        ),
                                                                        "value": "mgmt-ecology-endangered-species"  # valor del switch
                                                                    }
                                                                ],
                                                                value=[],  # sin selección por defecto
                                                                switch=True,  # estilo interruptor
                                                            )
                                                        ]
                                                    )
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
                                value='tab-management',  # tab seleccionada por defecto
                                className="tabs mb-2",  # clases CSS
                                children=[  # pestañas
                                    dcc.Tab(label='Management Scenarios', value='tab-management'),  # tab 1
                                    dcc.Tab(label='Saltmarsh evolution',  value='tab-saltmarsh'),  # tab 2
                                    dcc.Tab(label='Physical Accounts',    value='tab-physical'),  # tab 3
                                    dcc.Tab(label='EVA Overscale', value='tab-eva-overscale'),  # tab 4
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
                    # almacen para los EVA-Overscale funcional groups: 
                    dcc.Store(id="fg-selected-index"),
                    dcc.Store(id="fg-last-click-ts", data=0),
                    dcc.Store(id="fg-configs", data={}),
                    dcc.Store(id = "eva-overscale-draw-meta", data={"layer": "study-area", "color": "#015B97"}),
                    dcc.Store(id = "eva-overscale-file-store"),

                    # Debug Store:
                    # html.Pre(id="eva-debug", style={"display": "none"}),

                    # almacen para los layer de activities additional information
                    dcc.Store(id="layer-order", data=[]),

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

