from dash.dependencies import Input, Output, State
from dash import html, dcc
from shapely.geometry import shape
from shapely.validation import explain_validity

def register_draw_callbacks(app):
    @app.callback(
        Output('polygon-geojson', 'data'),
        Input('edit-control', 'geojson'),
        State('error-store', 'data')
    )
    def _update_polygon(geojson, errors):
        # Aquí va la validación de geometría y el almacenamiento en Store
        return dash.no_update
