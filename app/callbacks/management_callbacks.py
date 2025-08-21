# management_callbacks.py
import dash
from dash import Input, Output, State, no_update, html
from dash.exceptions import PreventUpdate
import dash_leaflet as dl
import json, time

COLOR = {
    "wind-farm-draw": "#f59e0b",
    "aquaculture-draw": "#22c55e",
    "vessel-draw": "#3b82f6",
    "defence-draw": "#ef4444",
}

# mapping de botones -> (layer_key, color)
BTN_META = {
    "wind-farm-draw": ("wind",   "#f59e0b"),
    "aquaculture-draw": ("aqua", "#22c55e"),
    "vessel-draw": ("vessel",    "#3b82f6"),
    "defence-draw": ("defence",  "#ef4444"),
}

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

    # 1) Pulsar DRAW -> fija capa de destino + color, y activa modo polígono
    @app.callback(
        Output("draw-meta", "data"),
        Output("edit-control", "drawToolbar"),
        Input("wind-farm-draw", "n_clicks"),
        Input("aquaculture-draw", "n_clicks"),
        Input("vessel-draw", "n_clicks"),
        Input("defence-draw", "n_clicks"),
        prevent_initial_call=True
    )
    def pick_target_and_activate(wf, aq, vs, df):
        if not (wf or aq or vs or df):
            raise PreventUpdate
        ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        layer_key, color = BTN_META[ctx]
        return {"layer": layer_key, "color": color}, {"mode": "polygon", "n_clicks": int(time.time())}

    # 2) Al terminar el dibujo -> copiar a la FeatureGroup destino y limpiar el EditControl
    @app.callback(
        Output("mgmt-wind", "children"),
        Output("mgmt-aqua", "children"),
        Output("mgmt-vessel", "children"),
        Output("mgmt-defence", "children"),
        Output("draw-len", "data"),
        Output("edit-control", "editToolbar"),
        Input("edit-control", "geojson"),
        State("draw-len", "data"),
        State("draw-meta", "data"),
        State("mgmt-wind", "children"),
        State("mgmt-aqua", "children"),
        State("mgmt-vessel", "children"),
        State("mgmt-defence", "children"),
        prevent_initial_call=True
    )
    def on_geojson(gj, prev_len, meta, ch_wind, ch_aqua, ch_vessel, ch_defence):
        feats = (gj or {}).get("features", [])
        n = len(feats)
        prev_len = prev_len or 0
        if n <= prev_len:
            raise PreventUpdate  # no hay nuevo dibujo (o viene del clear)

        # último creado por el control
        f = feats[-1]
        geom = (f or {}).get("geometry", {})
        gtype = geom.get("type")

        # preparar listas actuales
        ch_wind    = list(ch_wind or [])
        ch_aqua    = list(ch_aqua or [])
        ch_vessel  = list(ch_vessel or [])
        ch_defence = list(ch_defence or [])

        # función auxiliar
        def to_positions(coords):
            # GeoJSON [lon,lat] -> Leaflet [lat,lon]
            return [[lat, lon] for lon, lat in coords]

        # construir polígonos destino según tipo
        new_polys = []
        if gtype == "Polygon":
            ring = geom["coordinates"][0]
            new_polys = [to_positions(ring)]
        elif gtype == "MultiPolygon":
            new_polys = [to_positions(poly[0]) for poly in geom["coordinates"]]
        else:
            # ignoramos otros tipos
            clear = {"mode": "remove", "action": "clear all", "n_clicks": int(time.time())}
            return ch_wind, ch_aqua, ch_vessel, ch_defence, 0, clear

        # color/capa destino
        color = (meta or {}).get("color", "#ff00ff")
        layer = (meta or {}).get("layer", "wind")

        # crear componentes dl.Polygon con ese color
        poly_components = [
            dl.Polygon(positions=pos, color=color, fillColor=color, fillOpacity=0.6, weight=4)
            for pos in new_polys
        ]

        # volcar en la FeatureGroup correcta
        if layer == "wind":
            ch_wind.extend(poly_components)
        elif layer == "aqua":
            ch_aqua.extend(poly_components)
        elif layer == "vessel":
            ch_vessel.extend(poly_components)
        elif layer == "defence":
            ch_defence.extend(poly_components)

        # limpiar lo del control (gris) y RESETEAR el contador a 0
        clear = {"mode": "remove", "action": "clear all", "n_clicks": int(time.time())}
        return ch_wind, ch_aqua, ch_vessel, ch_defence, 0, clear
        


