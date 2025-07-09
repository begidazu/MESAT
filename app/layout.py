from dash import html, dcc
import dash_leaflet as dl

# Styles comunes
SIDEBAR_STYLE = {
    'width': '500px',
    'backgroundColor': '#C0D4EA',  # color claro
    'padding': '20px',
    'boxShadow': '0 0 10px rgba(0,0,0,0.2)',
    'height': '100vh',
    'overflowY': 'auto'
}
TAB_STYLE = {
    'padding': '10px 20px',
    'backgroundColor': '#7DA7D9',
    'color': 'white',
    'fontWeight': 'bold',
    'border': 'none'
}
TAB_SELECTED_STYLE = {
    **TAB_STYLE,
    'backgroundColor': '#5A88C7'
}

# Layout general de la aplicación

def create_layout():
    return html.Div([
        # Mapa a pantalla completa
        html.Div(
            dl.Map(
                id='map',
                center=[40, -3],
                zoom=6,
                style={'width': '100%', 'height': '100%'},
                children=[
                    dl.TileLayer(),
                    dl.FeatureGroup(id='draw-layer', children=[
                        dl.EditControl(
                            id='edit-control',
                            position='topright',
                            draw={'polygon': True,
                                  'polyline': False,
                                  'rectangle': False,
                                  'circle': False,
                                  'marker': False
                                  },
                            edit={'remove': True}
                        )
                    ])
                ]
            ),
            style={'flex': '1', 'position': 'relative'}
        ),
        # Sidebar con Tabs y contenido dinámico
        html.Div([
            dcc.Tabs(
                id='tabs',
                value='tab-saltmarsh',
                children=[
                    dcc.Tab(label='Saltmarsh evolution', value='tab-saltmarsh', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                    dcc.Tab(label='Fish Stock Evolution', value='tab-fishstock', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                    dcc.Tab(label='Physical Accounts', value='tab-physical', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                    dcc.Tab(label='Management Scenarios', value='tab-management', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE)
                ]
            ),
            # Contenedor dinámico para cada pestaña
            html.Div(id='tab-content', style={'marginTop': '20px'})
        ], style=SIDEBAR_STYLE)
    ], style={'display': 'flex', 'height': '100vh', 'margin': '0'})
