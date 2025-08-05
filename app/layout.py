# # app/layout.py
# from dash import html, dcc
# import dash_leaflet as dl
# import dash_bootstrap_components as dbc
# from dash_extensions.javascript import assign

# # Styles comunes
# SIDEBAR_STYLE = {
#     'width': '30%',               # Ocupa 25% del ancho
#     'backgroundColor': '#C0D4EA',
#     'padding': '0px',             # Sin padding para alinear al mapa
#     'boxShadow': '0 0 10px rgba(0,0,0,0.2)',
#     'height': '100vh',
#     'overflowY': 'auto',          # Scroll interno si el contenido excede
#     'boxSizing': 'border-box',     # Incluye padding/borde en la altura
#     'borderLeft': '1px solid black',
#     'position': 'relative'
# }
# # Contenedor para las tabs con padding interno
# TAB_CONTAINER_STYLE = {
#     'padding': '20px 20px 0 20px',
#     'boxSizing': 'border-box'
# }
# # Estilo para el contenido de la pestaña (dropdowns, gráficas, etc.)
# CONTENT_STYLE = {
#     'marginTop': '20px',
#     'padding': '20px',            # Espacio alrededor del contenido
#     'boxSizing': 'border-box'
# }

# # Estilos de Tabs
# TAB_STYLE = {
#     'display': 'flex',
#     'alignItems': 'center',
#     'justifyContent': 'center',
#     'padding': '10px 20px',
#     'backgroundColor': '#669FE4',
#     'color': 'white',
#     'fontWeight': 'bold',
#     'fontSize': '24px',
#     'border': '1px solid #274274',
#     'borderRadius': '4px 4px 0 0',
#     'marginRight': '2px'
# }
# TAB_SELECTED_STYLE = {
#     **TAB_STYLE,
#     'backgroundColor': "#255392"
# }

# # Layout general de la aplicación
# def create_layout():
#     return html.Div([
#         # Mapa
#         html.Div(
#             dl.Map(
#             id='map',
#             center=[40, -3],
#             zoom=6,
#             style={'width': '100%', 'height': '100%'},
#             children=[
#                 dl.TileLayer(),
#                 dl.FeatureGroup(id='draw-layer', children=[
#                     dl.EditControl(
#                         id='edit-control',
#                         position='topright',
#                         draw={
#                             'polygon': True,
#                             'polyline': False,
#                             'rectangle': False,
#                             'circle': False,
#                             'marker': False
#                         },
#                         edit={'remove': True}
#                     )
#                 ]),
#                 dl.FeatureGroup(id='raster-layer', children=[]), 
#                 dl.FeatureGroup(id='popup-layer', children=[])
#                 ]
#             ), id = 'map-box', style={'flex': '1', 'position': 'relative', 'boxSizing': 'border-box'}         
#         ),

#         # Sidebar con Tabs y contenido
#         html.Div([
#             # Wrapper para las pestañas
#             html.Div(
#                 dcc.Tabs(
#                     id='tabs',
#                     value='tab-saltmarsh',
#                     children=[
#                         dcc.Tab(label='Saltmarsh evolution', value='tab-saltmarsh', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
#                         dcc.Tab(label='Fish Stocks', value='tab-fishstock', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
#                         dcc.Tab(label='Physical Accounts', value='tab-physical', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
#                         dcc.Tab(label='Management Scenarios', value='tab-management', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE)
#                     ],
#                     style={'marginBottom': '0'}
#                 ),
#                 style=TAB_CONTAINER_STYLE
#             ),
#             # Contenedor dinámico de contenido de pestaña
#             html.Div(id='tab-content', style=CONTENT_STYLE),
#              # Enlaces al final del sidebar
#             html.Div([
#                 html.A([
#                     html.Span('📄', style={'fontSize': '40px', 'marginRight': '8px'}),  # Icono documento grande
#                     "Access the methodology"
#                 ], href='https://doi.org/10.1016/j.scitotenv.2024.178164', target='_blank', style={'display': 'flex', 'alignItems': 'center', 'color': 'black', 'textDecoration': 'none', 'marginTop': '20px'}),
#                 html.A([
#                     html.Img(src='/assets/logos/github-mark.png', style={'width': '40px', 'height': '40px', 'marginRight': '14px', 'marginLeft': '8px'}),
#                     "Access the code"
#                 ], href='https://github.com/begidazu/PhD_Web_App', target='_blank', style={'display': 'flex', 'alignItems': 'center', 'color': 'black', 'textDecoration': 'none', 'marginTop': '10px'})
#             ], style={'position': 'absolute', 'bottom': '30px', 'left': '30px', 'right': '20px', 'fontSize': '22px'})
#         ], style=SIDEBAR_STYLE)
#     ], style={
#         'display': 'flex',
#         'position': 'absolute',
#         'top': '1px',
#         'left': '1px',
#         'right': '1px',
#         'bottom': '1px',
#         'margin': '0',
#         'border': '3px solid black',
#         'boxSizing': 'border-box',   # incluye borde en la altura total
#         'overflow': 'hidden'          # sin scroll global
#     })


# app/layout.py

from dash import html, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc

def create_layout():
    return html.Div(
        # Este Div padre forzará la app a ocupar el 100% de la ventana
        dbc.Container(
            fluid=True,
            className="h-100 p-0",
            children=[
                dbc.Row(
                    className="h-100 g-0",
                    children=[
                        # === Columna del mapa (75%) ===
                        dbc.Col(
                            width=8,
                            className="p-0",
                            children=[
                                dl.Map(
                                    id='map',
                                    center=[40, -3],
                                    zoom=6,
                                    style={'width': '100%', 'height': '100%'},
                                    children=[
                                        dl.TileLayer(),
                                        dl.FeatureGroup(
                                            id='draw-layer',
                                            children=[
                                                dl.EditControl(
                                                    id='edit-control',
                                                    position='topright',
                                                    draw={
                                                        'polygon': True,
                                                        'polyline': False,
                                                        'rectangle': False,
                                                        'circle': False,
                                                        'marker': False
                                                    },
                                                    edit={'remove': True}
                                                )
                                            ]
                                        ),
                                        dl.FeatureGroup(id='raster-layer', children=[]),
                                        dl.FeatureGroup(id='popup-layer', children=[])
                                    ]
                                )
                            ]
                        ),
                        # === Sidebar (25%) ===
                        dbc.Col(
                            width=4,
                            className="bg-light border-start d-flex flex-column",
                            children=[
                                # Pestañas
                                dcc.Tabs(
                                    id='tabs',
                                    value='tab-saltmarsh',
                                    className="mb-3",
                                    children=[
                                        dcc.Tab(label='Saltmarsh evolution',  value='tab-saltmarsh'),
                                        dcc.Tab(label='Fish Stocks',          value='tab-fishstock'),
                                        dcc.Tab(label='Physical Accounts',    value='tab-physical'),
                                        dcc.Tab(label='Management Scenarios', value='tab-management'),
                                    ]
                                ),
                                # Contenido dinámico de pestaña
                                html.Div(
                                    id='tab-content',
                                    className="flex-grow-1 overflow-auto p-2 bg-white rounded shadow-sm"
                                ),
                                # Enlaces al final
                                html.Div(
                                    [
                                        html.A(
                                            [html.Span('📄', className="me-2"), "Access the methodology"],
                                            href='https://doi.org/10.1016/j.scitotenv.2024.178164',
                                            target='_blank',
                                            className="d-flex align-items-center mb-2 text-decoration-none text-dark"
                                        ),
                                        html.A(
                                            [html.Img(src='/assets/logos/github-mark.png', height="30", className="me-2"), "Access the code"],
                                            href='https://github.com/begidazu/PhD_Web_App',
                                            target='_blank',
                                            className="d-flex align-items-center text-decoration-none text-dark"
                                        )
                                    ],
                                    className="mt-auto p-2"
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        style={
            'height': '100vh',    # fuerza el alto completo de la ventana
            'margin': 0,
            'padding': 0,
            'display': 'flex'     # mantiene el flex a nivel root
        }
    )
