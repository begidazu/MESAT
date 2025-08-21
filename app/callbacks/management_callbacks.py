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
        Output("current-color", "data"),
        Output("edit-control", "drawToolbar"),
        Input("wind-farm-draw", "n_clicks"),
        prevent_initial_call=True
    )
    def activar_dibujo_poligono(n):
        if not n:
            raise PreventUpdate
        return "#f59e0b", {"mode": "polygon", "n_clicks": int(time.time())}
    
    @app.callback(
        Output("mgmt-layer", "children"),
        Input("edit-control", "geojson"),
        State("draw-len", "data"),
        State("current-color", "data"),
        State("mgmt-layer", "children"),
        prevent_initial_call=True
    )
    def on_geojson(gj, prev_len, color, children):
        feats = (gj or {}).get("features", [])
        n = len(feats)
        prev_len = prev_len or 0
        if n <= prev_len:
            raise PreventUpdate  # no hay nuevo dibujo

        f = feats[-1]  # último creado
        geom = (f or {}).get("geometry", {})
        gtype = geom.get("type")
        children = list(children or [])

        def to_positions(coords):
            # GeoJSON [lon, lat] -> Leaflet [lat, lon]
            return [[lat, lon] for lon, lat in coords]

        added = 0
        if gtype == "Polygon":
            ring = geom["coordinates"][0]
            children.append(dl.Polygon(
                positions=to_positions(ring),
                color=color or "#ff00ff",
                fillColor=color or "#ff00ff",
                fillOpacity=0.6,
                weight=4
            ))
            added = 1
        elif gtype == "MultiPolygon":
            for poly in geom["coordinates"]:
                ring = poly[0]
                children.append(dl.Polygon(
                    positions=to_positions(ring),
                    color=color or "#ff00ff",
                    fillColor=color or "#ff00ff",
                    fillOpacity=0.6,
                    weight=4
                ))
            added = 1

        # limpiar lo del EditControl para que no tape
        clear = {"mode": "remove", "action": "clear all", "n_clicks": int(time.time())}
        dbg = f"Nuevo: {gtype}, total mgmt-layer={len(children)} (añadido={added}), color={color}"
        return children#, 0, clear, dbg
        
 


