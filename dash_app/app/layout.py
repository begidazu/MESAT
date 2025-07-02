from dash import html, dcc
import dash_leaflet as dl

def create_layout():
    return html.Div([
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
                            draw={'polygon': True, 'polyline': False, 'rectangle': False, 'circle': False, 'marker': False},
                            edit={'remove': True}
                        )
                    ])
                ]
            ),
            style={'flex': '1', 'position': 'relative'}
        ),
        html.Div(id='sidebar'),
        dcc.Store(id='polygon-geojson', data={}),
        dcc.Store(id='error-store', data=[])
    ], style={'display': 'flex', 'height': '100vh', 'margin': '0'})
