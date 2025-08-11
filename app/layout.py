#app\layout.py

from dash import html, dcc
import dash_leaflet as dl
import dash_bootstrap_components as dbc

# Layout completamente flexible y responsive usando utilidades de Bootstrap
def create_layout():
    return html.Div(
        className="d-flex flex-column vh-100 p-0",
        children=[
            # Fila principal que ocupa todo el espacio disponible
            dbc.Row(
                className="flex-grow-1 g-0",
                children=[
                    # Columna del mapa: 8/12 en LG, 12/12 en MD/SM
                    dbc.Col(
                        lg=8, md=12, sm=12,
                        className="d-flex flex-column p-0",
                        children=[
                            # Mapa ocupa todo el espacio restante de la columna
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
                    # Sidebar: 4/12 en LG, 12/12 en MD/SM
                    dbc.Col(
                        lg=4, md=12, sm=12,
                        className="d-flex flex-column bg-light",
                        children=[
                            # Pestañas
                            dcc.Tabs(
                                id='tabs',
                                value='tab-saltmarsh',
                                className="tabs mb-2",
                                children=[
                                    dcc.Tab(label='Saltmarsh evolution',  value='tab-saltmarsh'),
                                    dcc.Tab(label='Fish Stocks',          value='tab-fishstock'),
                                    dcc.Tab(label='Physical Accounts',    value='tab-physical'),
                                    dcc.Tab(label='Management Scenarios', value='tab-management'),
                                ],
                                style={'fontWeight': 'bold'}
                            ),
                            # Contenido de pestaña ocupa resto y puede scrollearse
                            html.Div(
                                id='tab-content',
                                className="flex-grow-1 overflow-auto p-2 bg-white rounded shadow-sm"
                            ),
                            # Enlaces fijos abajo
                            html.Div(
                                className="p-2 mt-auto",
                                children=[
                                    html.A(
                                        [html.Span('📄', className="me-1"), "Access the methodology"],
                                        href='https://doi.org/10.1016/j.scitotenv.2024.178164',
                                        target='_blank',
                                        className="d-flex align-items-center text-decoration-none text-dark mb-1"
                                    ),
                                    html.A(
                                        [html.Img(src='/assets/logos/github-mark.png', height="24", className="me-1"), "Access the code"],
                                        href='https://github.com/begidazu/PhD_Web_App',
                                        target='_blank',
                                        className="d-flex align-items-center text-decoration-none text-dark"
                                    )
                                ]
                            )
                        ]
                    )
                ] 
            )
        ]
    )
