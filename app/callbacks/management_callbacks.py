# management_callbacks.py
import dash
from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate
import json, time

def register_management_callbacks(app: dash.Dash):

    # (1) Enable/disable por checklist (tu versión correcta)
    @app.callback(
        Output('wind-farm-draw', 'disabled'),
        Output('wind-farm-file', 'disabled'),
        Output('aquaculture-draw', 'disabled'),
        Output('aquaculture-file', 'disabled'),
        Output('vessel-draw', 'disabled'),
        Output('vessel-file', 'disabled'),
        Output('defence-draw', 'disabled'),
        Output('defence-file', 'disabled'),
        Input('wind-farm', 'value'),
        Input('aquaculture', 'value'),
        Input('vessel', 'value'),
        Input('defence', 'value'),
    )
    def toggle_controls(v_wind, v_aqua, v_vessel, v_defence):
        off = lambda v: not bool(v)
        return (
            off(v_wind), off(v_wind),
            off(v_aqua), off(v_aqua),
            off(v_vessel), off(v_vessel),
            off(v_defence), off(v_defence),
        )

    @app.callback(
        Output("edit-control", "drawToolbar"),
        Input("wind-farm-draw", "n_clicks"),
        prevent_initial_call=True
    )
    def activar_dibujo_poligono(n):
        if not n:
            raise PreventUpdate
        # Ponemos el modo en 'polygon' y devolvemos n_clicks para asegurar que el prop cambia
        return dict(mode = "polygon", n_clicks=n)