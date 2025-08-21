# management_callbacks.py
import dash
from dash import Input, Output, State, no_update, html
from dash.exceptions import PreventUpdate
import dash_leaflet as dl
import json, time

# mapping de botones -> (layer_key, color)
COLOR = {
    "wind-farm-draw": ("wind",   "#f39c12"),
    "aquaculture-draw": ("aqua", "#18BC9C"),
    "vessel-draw": ("vessel",    "#3498DB"),
    "defence-draw": ("defence",  "#e74c3c"),
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
        layer_key, color = COLOR[ctx]
        return {"layer": layer_key, "color": color}, {"mode": "polygon", "n_clicks": int(time.time())}

    # 2) Pintamos los poligonos en el mapa y los almacenamos en el FeatureGrop correspondiente.
    # Tambien limpiamos los FeatureGroup si el trigger fue un checklist.
    @app.callback(
        Output("mgmt-wind", "children"),
        Output("mgmt-aqua", "children"),
        Output("mgmt-vessel", "children"),
        Output("mgmt-defence", "children"),
        Output("draw-len", "data"),
        Output("edit-control", "editToolbar"),
        Input("edit-control", "geojson"),
        Input("wind-farm", "value"),
        Input("aquaculture", "value"),
        Input("vessel", "value"),
        Input("defence", "value"),
        State("draw-len", "data"),
        State("draw-meta", "data"),
        State("mgmt-wind", "children"),
        State("mgmt-aqua", "children"),
        State("mgmt-vessel", "children"),
        State("mgmt-defence", "children"),
        prevent_initial_call=True
    )
    def manage_layers(gj, v_wind, v_aqua, v_vessel, v_defence,
                    prev_len, meta, ch_wind, ch_aqua, ch_vessel, ch_defence):
        ctx = dash.callback_context
        trig = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Normaliza children actuales
        ch_wind    = list(ch_wind or [])
        ch_aqua    = list(ch_aqua or [])
        ch_vessel  = list(ch_vessel or [])
        ch_defence = list(ch_defence or [])

        # --- 1) Si el trigger fue un checklist -> limpiar capas deseleccionadas ---
        if trig in ("wind-farm", "aquaculture", "vessel", "defence"):
            if not bool(v_wind):
                ch_wind = []
            if not bool(v_aqua):
                ch_aqua = []
            if not bool(v_vessel):
                ch_vessel = []
            if not bool(v_defence):
                ch_defence = []

            # No tocar ni contador ni toolbar del control
            return ch_wind, ch_aqua, ch_vessel, ch_defence, no_update, no_update

        # --- 2) Si el trigger fue el geojson -> copiar último dibujo y limpiar el control ---
        feats = (gj or {}).get("features", [])
        n = len(feats)
        prev_len = prev_len or 0
        if n <= prev_len:
            raise PreventUpdate  # sin nuevo dibujo (o updates del clear)

        f = feats[-1]
        geom = (f or {}).get("geometry", {})
        gtype = geom.get("type")

        def to_positions(coords):
            # GeoJSON [lon,lat] -> Leaflet [lat,lon]
            return [[lat, lon] for lon, lat in coords]

        new_polys = []
        if gtype == "Polygon":
            new_polys = [to_positions(geom["coordinates"][0])]
        elif gtype == "MultiPolygon":
            new_polys = [to_positions(poly[0]) for poly in geom["coordinates"]]
        else:
            # Tipo no soportado: solo resetea contador y limpia el control
            clear = {"mode": "remove", "action": "clear all", "n_clicks": int(time.time())}
            return ch_wind, ch_aqua, ch_vessel, ch_defence, 0, clear

        color = (meta or {}).get("color", "#ff00ff")
        layer = (meta or {}).get("layer", "wind")
        comps = [dl.Polygon(positions=p, color=color, fillColor=color, fillOpacity=0.6, weight=4)
                for p in new_polys]

        if layer == "wind":
            ch_wind.extend(comps)
        elif layer == "aqua":
            ch_aqua.extend(comps)
        elif layer == "vessel":
            ch_vessel.extend(comps)
        elif layer == "defence":
            ch_defence.extend(comps)

        # Limpia el EditControl y resetea contador para evitar "azules intermedios"
        clear = {"mode": "remove", "action": "clear all", "n_clicks": int(time.time())}
        return ch_wind, ch_aqua, ch_vessel, ch_defence, 0, clear

        


