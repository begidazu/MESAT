# management_callbacks.py
import os, base64, uuid
import dash
from dash import Input, Output, State, no_update, html, dcc, dash_table
from dash.exceptions import PreventUpdate
import dash_leaflet as dl
import json, time
import shutil
from pathlib import Path 
import pandas as pd                                              # leer parquet con pandas
try:                                                             # intentar importar geopandas
    import geopandas as gpd                                      # geopandas para GeoParquet
except Exception:                                                # si no está disponible
    gpd = None                                                   # marcamos no disponible
try:                                                             # intentar importar shapely
    from shapely import wkt as shp_wkt                           # parser de WKT
    from shapely import wkb as shp_wkb                           # parser de WKB
    from shapely.geometry import mapping, Point                  # convertir geometrías a GeoJSON + puntos
except Exception:                                                # si no está disponible shapely
    shp_wkt = shp_wkb = mapping = Point = None

from app.models.management_scenarios import (
    eunis_available, saltmarsh_available, activity_eunis_table,
    activity_saltmarsh_table, saltmarsh_scenario_available, saltmarsh_scenario_years,
    activity_saltmarsh_scenario_table)

# mapping de botones -> (layer_key, color)
COLOR = {
    "wind-farm-draw": ("wind",   "#f39c12"),
    "aquaculture-draw": ("aqua", "#18BC9C"),
    "vessel-draw": ("vessel",    "#3498DB"),
    "defence-draw": ("defence",  "#e74c3c"),
}

# Clase base FORMS:
UPLOAD_CLASS = "form-control form-control-lg"
# Clase base del upload:
BASE_UPLOAD_CLASS = "form-control is-valid form-control-lg"
# Clase para upload invalido:                 
INVALID_UPLOAD_CLASS = "form-control is-invalid form-control-lg"   

# Keys of the saltmarshs cenarios
SCEN_LABEL = {
    "regional_rcp45": "Regional RCP4.5",
    "regional_rcp85": "Regional RCP8.5",
    "global_rcp45":   "Global RCP4.5",
}
SCEN_KEYS = ["regional_rcp45", "regional_rcp85", "global_rcp45"]

def _render_table(df, empty_text):
    if df is None or df.empty:
        return html.Div(empty_text, className="text-muted", style={"padding":"8px"})
    table = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in df.columns],
        data=df.to_dict("records"),
        sort_action="native", filter_action="native", page_action="none",
        style_table={"maxHeight":"720px","overflowY":"auto","border":"1px solid #ddd","borderRadius":"8px"},
        style_cell={"padding":"8px","fontSize":"1.0rem","textAlign":"center"},
        style_header={"fontWeight":"bold","backgroundColor":"#f7f7f7","borderBottom":"1px solid #ccc"},
        style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}]
    )
    return html.Div([html.Hr(), table], style={"marginTop":"8px"})


def _build_saltmarsh_scenarios_layout(area: str,
                                      mgmt_w, mgmt_wu,
                                      mgmt_a, mgmt_au,
                                      mgmt_v, mgmt_vu,
                                      mgmt_d, mgmt_du):

    def _years_tabs_for(activity_key: str, act_children, act_upload_children):
        scen_tabs = []
        for scen in SCEN_KEYS:
            if not saltmarsh_scenario_available(area, scen):
                continue
            years = saltmarsh_scenario_years(area, scen)
            if not years:
                continue

            # Precalcular tablas para TODOS los años de este escenario:
            year_tabs = []
            for y in years:
                try:
                    df = activity_saltmarsh_scenario_table(area, scen, y, act_children, act_upload_children)
                    div = _render_table(df, f"No saltmarshes and mudflats within polygons for {SCEN_LABEL[scen]} {y}.")
                except Exception as e:
                    import traceback; traceback.print_exc()
                    div = html.Div(f"Error building table ({SCEN_LABEL[scen]} {y}): {e}",
                                   style={"color":"crimson","whiteSpace":"pre-wrap"})
                year_tabs.append(dcc.Tab(label=y, value=y, children=[div]))

            scen_tabs.append(
                dcc.Tab(
                    label=SCEN_LABEL[scen], value=scen,
                    children=[dcc.Tabs(
                        id=f"mgmt-scen-{activity_key}-years-{scen}",
                        value=years[0],  # default al primero
                        children=year_tabs,
                        style={"padding":"0.25rem 0.5rem"}
                    )],
                    style={"padding":"0.5rem 0.75rem"},
                    selected_style={"padding":"0.5rem 0.75rem"}
                )
            )

        # Si no hay ningún escenario disponible, devuelve placeholder
        if not scen_tabs:
            return html.Div("No saltmarsh scenario rasters available for this area.",
                            className="text-muted", style={"padding":"8px"})

        return dcc.Tabs(
            id=f"mgmt-scen-{activity_key}-scenarios",
            value=SCEN_KEYS[0],
            children=scen_tabs,
            style={"marginBottom":"0.5rem"}
        )

    def activity_panel(label, key, act_children, act_upload_children):
        return dcc.Tab(
            label=label, value=key,
            children=[
                _years_tabs_for(key, act_children, act_upload_children)
            ],
            style={"fontSize":"var(--font-lg)", "padding":"0.55rem 1rem"},
            selected_style={"fontSize":"var(--font-lg)", "padding":"0.55rem 1rem"},
        )

    # Sum all activities geometries for Total affection:
    def _as_list(x):
        if x is None:
            return []
        if isinstance(x, list):
            return x
        return [x]

    total_children = (_as_list(mgmt_w)  + _as_list(mgmt_a)  + _as_list(mgmt_v)  + _as_list(mgmt_d))
    total_upload_children = (_as_list(mgmt_wu) + _as_list(mgmt_au) + _as_list(mgmt_vu) + _as_list(mgmt_du))


    return dcc.Tabs(
        id="mgmt-scenarios-tabs-main", value="wind",
        children=[
            activity_panel("Wind Farms",   "wind",       mgmt_w,  mgmt_wu),
            activity_panel("Aquaculture",  "aquaculture",mgmt_a,  mgmt_au),
            activity_panel("Vessel Routes","vessel",     mgmt_v,  mgmt_vu),
            activity_panel("Defence",      "defence",    mgmt_d,  mgmt_du),
            activity_panel("TOTAL",        "total",      total_children, total_upload_children)
        ]
    )

# Funcion para validar la extension del fichero subido por los usuarios:
def _valid_ext(filename: str) -> bool:                                                
    if not filename:                                                                   # si no hay nombre no es valido
        return False                                                                   
    lower = filename.lower()                                                           # normalizar a minúsculas
    return lower.endswith(".json") or lower.endswith(".parquet")                       # aceptar solo .json o .parquet

# Funcion para crear la carpeta de la sesion como string:
def _session_dir(kind: str, session_id: str) -> str:
    if not isinstance(session_id, str) or not session_id:
        session_id = "anon"
    base = Path(os.getcwd()) / "uploads" / kind / session_id
    base.mkdir(parents=True, exist_ok=True)
    return str(base)

# Funcion para borrar el arbol, se usa para eliminar las carpetas de upload, teniendo en cuenta la sesion del usuario:
def _rm_tree(path: str) -> None:                                                      
    try:
        if path and Path(path).exists():
            shutil.rmtree(path, ignore_errors=True)                                   
    except Exception:
        pass

# Funcion que estima el tamano:
def _estimate_b64_size(contents: str) -> int:                                         
    if not contents or "," not in contents:
        return 0
    b64 = contents.split(",", 1)[1]
    # aproximación: cada 4 caracteres ~ 3 bytes
    return int(len(b64) * 3 / 4)

# Funcion que guarda el fichero en una carpeta correspondiente a la sesion para utilizarla mientras se usa la app. Despues con el codigo de limpieza en run.py se borra si la sesion es vieja:
def _save_upload_to_disk(contents: str, filename: str, kind: str, session_id: str) -> str: 
    if not contents or "," not in contents:
        raise ValueError("Upload contents malformed")
    header, b64 = contents.split(",", 1)
    data = base64.b64decode(b64)
    ext = os.path.splitext(filename)[1].lower()
    out_dir = _session_dir(kind, session_id)
    out_path = Path(out_dir) / f"{uuid.uuid4().hex}{ext}"
    with open(out_path, "wb") as f:
        f.write(data)
    return str(out_path)

# Funcion para detectar las columnas de lat/long de los ficheros pasados por el usaurio:
def _detect_lonlat_columns(df):                                   
    cols = {c.lower(): c for c in df.columns}                     
    lon_candidates = ["lon", "longitude", "x"]                    # candidatos a longitud
    lat_candidates = ["lat", "latitude", "y"]                     # candidatos a latitud
    lon_col = next((cols[c] for c in lon_candidates if c in cols), None)  # primera coincidencia lon
    lat_col = next((cols[c] for c in lat_candidates if c in cols), None)  # primera coincidencia lat
    return lon_col, lat_col                                       # devolver nombres

# Funcion para crear el feature collection:
def _df_to_feature_collection_from_polygon(df, lon_col, lat_col):  
    feats = []                                                    
    for _, row in df.dropna(subset=[lon_col, lat_col]).iterrows():# iterar por filas válidas
        try:                                                      
            lon = float(row[lon_col])                             # convertir lon a float
            lat = float(row[lat_col])                             # convertir lat a float
        except Exception:                                         # si falla la conversión saltar fila
            continue                                              
        props = row.drop([lon_col, lat_col]).to_dict()            # propiedades: resto de columnas
        feats.append({                                            # añadir feature
            "type": "Feature",                                    # tipo de entidad
            "geometry": {"type": "Polygon", "coordinates": [lon, lat]},  # polygon GeoJSON
            "properties": props                                   # propiedades
        })
    return {"type": "FeatureCollection", "features": feats}       # devolver FeatureCollection

# Funcion para pasar de .parquet a GeoJSON, que es lo que se va a usar para mostrar en el mapa y hacer calculos:
def _to_geojson_from_parquet(path):                               
    # 1) Intentar leer como GeoParquet con geopandas y hacer ajustes de proyecciones y otros check:
    if gpd is not None:                                           # si geopandas está disponible
        try:                                                      
            gdf = gpd.read_parquet(path)                          
            if gdf.empty:                                         
                return {"type": "FeatureCollection", "features": []}  
            if gdf.crs is not None:                               
                try:                                              
                    gdf = gdf.to_crs(4326)                        
                except Exception:                                 
                    pass                                          
            geojson = json.loads(gdf.to_json())                   
            return geojson                                        
        except Exception:                                         # si falla geopandas continuar con plan B
            pass                                                  

    # 2) Plan B: pandas + heurísticas (WKT, WKB, lon/lat)
    df = pd.read_parquet(path)                                    # leer parquet con pandas
    if df.empty:                                                  # si está vacío
        return {"type": "FeatureCollection", "features": []}      # devolver vacío

    lower_cols = {c.lower(): c for c in df.columns}               
    # 2.a) WKT en columna 'wkt' o similar
    wkt_col = next((lower_cols[c] for c in lower_cols if "wkt" in c), None)  # buscar columna WKT
    if wkt_col and shp_wkt is not None and mapping is not None:  # si hay WKT y shapely disponible
        feats = []                                                # lista de features
        for _, row in df.dropna(subset=[wkt_col]).iterrows():     # recorrer filas con WKT
            try:                                                  # proteger el parseo
                geom = shp_wkt.loads(str(row[wkt_col]))           # parsear WKT a geometría shapely
                geo = mapping(geom)                               # convertir a GeoJSON geometry
            except Exception:                                     # si falla el parseo
                continue                                          # saltar fila
            props = row.drop([wkt_col]).to_dict()                 # propiedades sin la columna WKT
            feats.append({"type": "Feature", "geometry": geo, "properties": props})  # añadir feature
        return {"type": "FeatureCollection", "features": feats}   # devolver FeatureCollection

    # 2.b) WKB en columna 'geometry' (bytes)
    geom_col = lower_cols.get("geometry")                         # posible columna 'geometry'
    if geom_col and shp_wkb is not None and mapping is not None:  # si hay WKB y shapely disponible
        feats = []                                                # lista de features
        for _, row in df.dropna(subset=[geom_col]).iterrows():    # recorrer filas con geometría
            try:                                                  # proteger parseo
                geom = shp_wkb.loads(row[geom_col])               # parsear WKB a geometría shapely
                geo = mapping(geom)                               # convertir a geometry GeoJSON
            except Exception:                                     # si falla
                continue                                          # saltar fila
            props = row.drop([geom_col]).to_dict()                # propiedades sin la columna de geometría
            feats.append({"type": "Feature", "geometry": geo, "properties": props})  # añadir feature
        return {"type": "FeatureCollection", "features": feats}   # devolver FeatureCollection

    # 2.c) lon/lat
    lon_col, lat_col = _detect_lonlat_columns(df)                 # detectar pares lon/lat
    if lon_col and lat_col:                                       # si existen columnas lon/lat
        return _df_to_feature_collection_from_polygon(df, lon_col, lat_col)  # construir FeatureCollection

    # 2.d) si no se pudo inferir geometría, devolver vacío
    return {"type": "FeatureCollection", "features": []}          # devolver vacío si no hay geometría detectable

# Function to build tabs where we will store the management scenarios affection graphs:
def _build_mgmt_tabs(eunis_enabled: bool, saltmarsh_enabled: bool):

    def _subtabs(slug):
        return dcc.Tabs(
            id=f"mgmt-{slug}-subtabs",
            value="eunis",
            children=[
                dcc.Tab(
                    label="EUNIS", value="eunis",
                    style={"fontSize": "var(--font-md)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    disabled=not eunis_enabled,
                    children=[html.Div(id=f"mgmt-{slug}-eunis", children="(tabla EUNIS)")]
                ),
                dcc.Tab(
                    label="Saltmarshes", value="saltmarshes",
                    style={"fontSize": "var(--font-md)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    disabled=not saltmarsh_enabled,
                    children=[html.Div(id=f"mgmt-{slug}-saltmarshes", children="(tabla Saltmarshes)")]
                ),
                dcc.Tab(
                    label="Fish", value="fish",
                    style={"fontSize": "var(--font-md)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    children=[html.Div(id=f"mgmt-{slug}-fish", children="(pendiente)")]
                ),
            ]
        )

# Function to create the layers of the additional information for the economic activities:
def make_additional_layer(key, z_index):
    # Ejemplos: reemplaza URLs reales
    if key == "A":
        tile = dl.WMSTileLayer(
            url="https://.../wms", layers="...", transparent=True,
            format="image/png", zIndex=z_index
        )
    else:  # key == "B"
        tile = dl.TileLayer(  # WMTS como plantilla de URL
            url="https://.../wmts?...&TileMatrix={z}&TileRow={y}&TileCol={x}",
            zIndex=z_index
        )
    # Envolvemos en Overlay para que aparezca en el LayersControl
    return dl.Overlay(name=key, checked=True, children=tile, id=f"ov-{key}")


    return dcc.Tabs(
        id="mgmt-main-tabs", value="wind",
        children=[
            dcc.Tab(label="Wind Farms", value="wind",
                    style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    children=[_subtabs("wind")]),
            dcc.Tab(label="Aquaculture", value="aquaculture",
                    style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    children=[_subtabs("aquaculture")]),
            dcc.Tab(label="Vessel Routes", value="vessel",
                    style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    children=[_subtabs("vessel")]),
            dcc.Tab(label="Defence", value="defence",
                    style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    children=[_subtabs("defence")]),
            dcc.Tab(label="TOTAL", value="total",
                    style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    selected_style={"fontSize": "var(--font-lg)", "padding": "0.55rem 1rem"},
                    children=[_subtabs("total")])                 
        ]
    )

# Definis los callbacks que vienen de la app para el tab-management:
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

    # 2) Pulsar DRAW -> fija capa de destino + color, y activa el modo polígono
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

    # 3) Pintamos los poligonos en el mapa y los almacenamos en el FeatureGrop correspondiente cuando el usuario acaba un poligono. Tambien limpiamos los FeatureGroup si el trigger fue un checklist.
    @app.callback(
        Output("mgmt-wind", "children"),
        Output("mgmt-aquaculture", "children"),
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
        State("mgmt-aquaculture", "children"),
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

    # Creamos una sesion si no existe para tenerlo en cuenta para eliminar los Upload viejos de los usuarios y manejar mejor la memoria:
    @app.callback(                                                                            
        Output("session-id", "data"),
        Input("tabs", "value"),
        State("session-id", "data"),
        prevent_initial_call=False
    )
    def ensure_session_id(_active_tab, sid):
        if sid:
            raise PreventUpdate
        return uuid.uuid4().hex


#--------------------------------------------------------- LOGIC OF DRAW AND UPLOAD BUTTONS OF THE MANAGEMENT SCENARIOS ------------------------------------------------------------------------------------------

    # Si el fichero no tiene la extension que queremos escribimos que no es valido, si es valido se guarda y se convierte a GeoJSON para ponerlo en el mapa (WIND):
    @app.callback(
        Output("wind-farm-file-label", "children", allow_duplicate=True),
        Output("wind-farm-file", "className", allow_duplicate=True),
        Output("wind-file-store", "data", allow_duplicate=True),
        Input("wind-farm-file", "filename"),
        Input("wind-farm-file", "contents"),
        State("wind-file-store", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def on_upload_wind(filename, contents, prev_store, sid):
        if not filename:
            raise PreventUpdate
        label_text = filename
        if not _valid_ext(filename):
            return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}
        if not contents:
            return label_text, BASE_UPLOAD_CLASS, no_update
        try:
            sid = sid if isinstance(sid, str) and sid else None
            out_path = _save_upload_to_disk(contents, filename, "wind", sid)
            # eliminar fichero previo de ESTA sesión si existía
            try:
                if isinstance(prev_store, dict) and prev_store.get("valid"):
                    old_path = prev_store.get("path")
                    if old_path and Path(old_path).exists() and sid in Path(old_path).parts:
                        Path(old_path).unlink(missing_ok=True)
            except Exception:
                pass
            payload = {
                "valid": True,
                "kind": "wind",
                "filename": filename,
                "ext": os.path.splitext(filename)[1].lower(),
                "path": out_path,
                "ts": int(time.time()),
                "sid": sid
            }
            return label_text, BASE_UPLOAD_CLASS, payload
        except Exception as e:
            return f"{filename} — error: {e}", INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}
        

    # Sincronizos la UI para que si hay un fichero subido por el usuario se deshabiliten el boton DRAW y el Upload, limpiar GeoJSON al deseleccionar checklist, restaurar texto del Upload, etc. (WIND)
    @app.callback(                                                                                              
        Output("wind-farm-draw", "disabled", allow_duplicate=True),                                            
        Output("wind-farm-file", "disabled", allow_duplicate=True),                                             
        Output("mgmt-wind", "children", allow_duplicate=True),                                                  
        Output("wind-file-store", "data", allow_duplicate=True),                                                
        Output("mgmt-wind-upload", "children", allow_duplicate=True),                                           
        Output("wind-farm-file-label", "children", allow_duplicate=True),
        Output("wind-farm-file", "filename", allow_duplicate=True),         # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("wind-farm-file", "contents", allow_duplicate=True),                               # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("wind-farm-file", "className"),                                     
        Input("wind-file-store", "data"),                                                                       
        Input("mgmt-wind", "children"),                                                                         
        Input("wind-farm", "value"),                                                                            
        State("session-id", "data"),
        prevent_initial_call=True                                                                              
    )
    def sync_wind_ui(store, drawn_children, wind_checked, sid):                                                
        selected = bool(wind_checked)                                                                           
        file_present = isinstance(store, dict) and store.get("valid") is True                                   

        # Caso 1: checklist desmarcado -> limpiar Store y polígonos, y dejar controles deshabilitados            
        if not selected:
            # borrar toda la carpeta de la sesión para wind
            try:
                _rm_tree(_session_dir("wind", sid))
            except Exception:
                pass                                                                                             
            return True, True, [], None, [], "Choose json or parquet file", None, None, UPLOAD_CLASS                               

        # Caso 2: checklist marcado y hay fichero válido -> bloquear Draw y Upload                              
        if file_present:                                                                                         
            return True, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update               

        # Caso 3: checklist marcado -> habilitar Draw y Upload; si hay algo pintado se deshabilita el upload                                 
        has_drawn = (isinstance(drawn_children, list) and len(drawn_children) > 0) or bool(drawn_children) # Condicion para evaluar si hay un poligono pintado
        return False, has_drawn, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update            

    # Callback que pinta el fichero en GeoJSON para los wind-farms (hacer lo mismo para las otras actividades y cambiar el color de los poligonos): (WIND)
    @app.callback(                                                                                  
        Output("mgmt-wind-upload", "children"),                                                     # salida: capa pintada en el mapa
        Input("wind-file-store", "data"),                                                           # entrada: cambios en el Store de wind
        prevent_initial_call=True                                                                   
    )
    def paint_wind_uploaded(data):                                                                  
        if not data or not isinstance(data, dict):                                                  
            raise PreventUpdate                                                                      # no actualizar si no hay nada
        if not data.get("valid"):                                                                   
            return []                                                                                # limpiar capa si hubo intento inválido

        path = data.get("path")                                                                      # ruta del archivo guardado en la carpeta de la sesion
        ext  = (data.get("ext") or "").lower()                                                      

        # estilo común para polígonos/líneas (Leaflet aplicará estilo a features no puntuales)       
        style = dict(color="#f39c12", weight=3, fillColor="#f39c12", fillOpacity=0.4)               # estilo Wind

        try:                                                                                         # intentar construir GeoJSON en memoria
            if ext == ".json":                                                                       # caso GeoJSON directo
                with open(path, "r", encoding="utf-8") as f:                                         # abrir fichero json
                    geo = json.load(f)                                                               # cargar a dict
            elif ext == ".parquet":                                                                  # caso Parquet -> GeoJSON
                geo = _to_geojson_from_parquet(path)                                                 # convertir parquet a GeoJSON dict
            else:                                                                                    # extensión no soportada
                return []                                                                            # no pintamos nada

            # proteger contra colecciones vacías para evitar zoom no deseado                        
            if not isinstance(geo, dict) or not geo.get("features"):                                 
                return []                                                                            

            layer = dl.GeoJSON(                                                                      # crear capa GeoJSON
                data=geo,                                                                            # pasar dict geojson
                zoomToBounds=True,                                                                   # ajustar mapa al contenido
                options=dict(style=style),                                                           # estilo para polígonos/líneas
                id=f"wind-upload-{data.get('ts', 0)}"                                                # id único por timestamp
            )
            return [layer]                                                                           # devolver lista con la capa
        except Exception:                                                                             
            return []         

    # Si el fichero no tiene la extension que queremos escribimos que no es valido, si es valido se guarda y se convierte a GeoJSON para ponerlo en el mapa (AQUACULTURE):
    @app.callback(
        Output("aquaculture-file-label", "children", allow_duplicate=True),
        Output("aquaculture-file", "className", allow_duplicate=True),
        Output("aquaculture-file-store", "data", allow_duplicate=True),
        Input("aquaculture-file", "filename"),
        Input("aquaculture-file", "contents"),
        State("aquaculture-file-store", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def on_upload_aquaculture(filename, contents, prev_store, sid):
        if not filename:
            raise PreventUpdate
        label_text = filename
        if not _valid_ext(filename):
            return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}
        if not contents:
            return label_text, BASE_UPLOAD_CLASS, no_update
        try:
            sid = sid if isinstance(sid, str) and sid else None
            out_path = _save_upload_to_disk(contents, filename, "aquaculture", sid)
            # eliminar fichero previo de ESTA sesión si existía
            try:
                if isinstance(prev_store, dict) and prev_store.get("valid"):
                    old_path = prev_store.get("path")
                    if old_path and Path(old_path).exists() and sid in Path(old_path).parts:
                        Path(old_path).unlink(missing_ok=True)
            except Exception:
                pass
            payload = {
                "valid": True,
                "kind": "aquaculture",
                "filename": filename,
                "ext": os.path.splitext(filename)[1].lower(),
                "path": out_path,
                "ts": int(time.time()),
                "sid": sid
            }
            return label_text, BASE_UPLOAD_CLASS, payload
        except Exception as e:
            return f"{filename} — error: {e}", INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}
        
    

    # Sincronizos la UI para que si hay un fichero subido por el usuario se deshabiliten el boton DRAW y el Upload, limpiar GeoJSON al deseleccionar checklist, restaurar texto del Upload, etc. (AQUACULTURE)
    @app.callback(                                                                                              
        Output("aquaculture-draw", "disabled", allow_duplicate=True),                                            
        Output("aquaculture-file", "disabled", allow_duplicate=True),                                             
        Output("mgmt-aquaculture", "children", allow_duplicate=True),                                                  
        Output("aquaculture-file-store", "data", allow_duplicate=True),                                                
        Output("mgmt-aquaculture-upload", "children", allow_duplicate=True),                                           
        Output("aquaculture-file-label", "children", allow_duplicate=True),
        Output("aquaculture-file", "filename", allow_duplicate=True),         # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("aquaculture-file", "contents", allow_duplicate=True),                               # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("aquaculture-file", "className"),                                     
        Input("aquaculture-file-store", "data"),                                                                       
        Input("mgmt-aquaculture", "children"),                                                                         
        Input("aquaculture", "value"),                                                                            
        State("session-id", "data"),
        prevent_initial_call=True                                                                              
    )
    def sync_aqua_ui(store, drawn_children, aqua_checked, sid):                                                
        selected = bool(aqua_checked)                                                                           
        file_present = isinstance(store, dict) and store.get("valid") is True                                   

        # Caso 1: checklist desmarcado -> limpiar Store y polígonos, y dejar controles deshabilitados            
        if not selected:
            # borrar toda la carpeta de la sesión para wind
            try:
                _rm_tree(_session_dir("aquaculture", sid))
            except Exception:
                pass                                                                                             
            return True, True, [], None, [], "Choose json or parquet file", None, None, UPLOAD_CLASS                               

        # Caso 2: checklist marcado y hay fichero válido -> bloquear Draw y Upload                              
        if file_present:                                                                                         
            return True, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update               

        # Caso 3: checklist marcado -> habilitar Draw y Upload; si hay algo pintado se deshabilita el upload                                 
        has_drawn = (isinstance(drawn_children, list) and len(drawn_children) > 0) or bool(drawn_children) # Condicion para evaluar si hay un poligono pintado
        return False, has_drawn, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    


    # Callback que pinta el fichero en GeoJSON para los wind-farms (hacer lo mismo para las otras actividades y cambiar el color de los poligonos): (AQUACULTURE)
    @app.callback(                                                                                  
        Output("mgmt-aquaculture-upload", "children"),                                                     # salida: capa pintada en el mapa
        Input("aquaculture-file-store", "data"),                                                           # entrada: cambios en el Store de wind
        prevent_initial_call=True                                                                   
    )
    def paint_aqua_uploaded(data):                                                                  
        if not data or not isinstance(data, dict):                                                  
            raise PreventUpdate                                                                      # no actualizar si no hay nada
        if not data.get("valid"):                                                                   
            return []                                                                                # limpiar capa si hubo intento inválido

        path = data.get("path")                                                                      # ruta del archivo guardado en la carpeta de la sesion
        ext  = (data.get("ext") or "").lower()                                                      

        # estilo común para polígonos/líneas (Leaflet aplicará estilo a features no puntuales)       
        style = dict(color="#18BC9C", weight=3, fillColor="#18BC9C", fillOpacity=0.4)               # estilo Wind

        try:                                                                                         # intentar construir GeoJSON en memoria
            if ext == ".json":                                                                       # caso GeoJSON directo
                with open(path, "r", encoding="utf-8") as f:                                         # abrir fichero json
                    geo = json.load(f)                                                               # cargar a dict
            elif ext == ".parquet":                                                                  # caso Parquet -> GeoJSON
                geo = _to_geojson_from_parquet(path)                                                 # convertir parquet a GeoJSON dict
            else:                                                                                    # extensión no soportada
                return []                                                                            # no pintamos nada

            # proteger contra colecciones vacías para evitar zoom no deseado                        
            if not isinstance(geo, dict) or not geo.get("features"):                                 
                return []                                                                            

            layer = dl.GeoJSON(                                                                      # crear capa GeoJSON
                data=geo,                                                                            # pasar dict geojson
                zoomToBounds=True,                                                                   # ajustar mapa al contenido
                options=dict(style=style),                                                           # estilo para polígonos/líneas
                id=f"aquaculture-upload-{data.get('ts', 0)}"                                                # id único por timestamp
            )
            return [layer]                                                                           # devolver lista con la capa
        except Exception:                                                                             
            return []         


    # Si el fichero no tiene la extension que queremos escribimos que no es valido, si es valido se guarda y se convierte a GeoJSON para ponerlo en el mapa (VESSEL ROUTES):
    @app.callback(
        Output("vessel-file-label", "children", allow_duplicate=True),
        Output("vessel-file", "className", allow_duplicate=True),
        Output("vessel-file-store", "data", allow_duplicate=True),
        Input("vessel-file", "filename"),
        Input("vessel-file", "contents"),
        State("vessel-file-store", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def on_upload_vessel(filename, contents, prev_store, sid):
        if not filename:
            raise PreventUpdate
        label_text = filename
        if not _valid_ext(filename):
            return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}
        if not contents:
            return label_text, BASE_UPLOAD_CLASS, no_update
        try:
            sid = sid if isinstance(sid, str) and sid else None
            out_path = _save_upload_to_disk(contents, filename, "vessel", sid)
            # eliminar fichero previo de ESTA sesión si existía
            try:
                if isinstance(prev_store, dict) and prev_store.get("valid"):
                    old_path = prev_store.get("path")
                    if old_path and Path(old_path).exists() and sid in Path(old_path).parts:
                        Path(old_path).unlink(missing_ok=True)
            except Exception:
                pass
            payload = {
                "valid": True,
                "kind": "vessel",
                "filename": filename,
                "ext": os.path.splitext(filename)[1].lower(),
                "path": out_path,
                "ts": int(time.time()),
                "sid": sid
            }
            return label_text, BASE_UPLOAD_CLASS, payload
        except Exception as e:
            return f"{filename} — error: {e}", INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}
        
    

    # Sincronizos la UI para que si hay un fichero subido por el usuario se deshabiliten el boton DRAW y el Upload, limpiar GeoJSON al deseleccionar checklist, restaurar texto del Upload, etc. (VESSEL ROUTES)
    @app.callback(                                                                                              
        Output("vessel-draw", "disabled", allow_duplicate=True),                                            
        Output("vessel-file", "disabled", allow_duplicate=True),                                             
        Output("mgmt-vessel", "children", allow_duplicate=True),                                                  
        Output("vessel-file-store", "data", allow_duplicate=True),                                                
        Output("mgmt-vessel-upload", "children", allow_duplicate=True),                                           
        Output("vessel-file-label", "children", allow_duplicate=True),
        Output("vessel-file", "filename", allow_duplicate=True),         # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("vessel-file", "contents", allow_duplicate=True),         # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("vessel-file", "className"),                                     
        Input("vessel-file-store", "data"),                                                                       
        Input("mgmt-vessel", "children"),                                                                         
        Input("vessel", "value"),                                                                            
        State("session-id", "data"),
        prevent_initial_call=True                                                                              
    )
    def sync_vessel_ui(store, drawn_children, aqua_checked, sid):                                                
        selected = bool(aqua_checked)                                                                           
        file_present = isinstance(store, dict) and store.get("valid") is True                                   

        # Caso 1: checklist desmarcado -> limpiar Store y polígonos, y dejar controles deshabilitados            
        if not selected:
            # borrar toda la carpeta de la sesión para wind
            try:
                _rm_tree(_session_dir("vessel", sid))
            except Exception:
                pass                                                                                             
            return True, True, [], None, [], "Choose json or parquet file", None, None, UPLOAD_CLASS                               

        # Caso 2: checklist marcado y hay fichero válido -> bloquear Draw y Upload                              
        if file_present:                                                                                         
            return True, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update               

        # Caso 3: checklist marcado -> habilitar Draw y Upload; si hay algo pintado se deshabilita el upload                                 
        has_drawn = (isinstance(drawn_children, list) and len(drawn_children) > 0) or bool(drawn_children) # Condicion para evaluar si hay un poligono pintado
        return False, has_drawn, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    


    # Callback que pinta el fichero en GeoJSON para los wind-farms (hacer lo mismo para las otras actividades y cambiar el color de los poligonos): (VESSEL ROUTES)
    @app.callback(                                                                                  
        Output("mgmt-vessel-upload", "children"),                                                     # salida: capa pintada en el mapa
        Input("vessel-file-store", "data"),                                                           # entrada: cambios en el Store de wind
        prevent_initial_call=True                                                                   
    )
    def paint_vessel_uploaded(data):                                                                  
        if not data or not isinstance(data, dict):                                                  
            raise PreventUpdate                                                                      # no actualizar si no hay nada
        if not data.get("valid"):                                                                   
            return []                                                                                # limpiar capa si hubo intento inválido

        path = data.get("path")                                                                      # ruta del archivo guardado en la carpeta de la sesion
        ext  = (data.get("ext") or "").lower()                                                      

        # estilo común para polígonos/líneas (Leaflet aplicará estilo a features no puntuales)       
        style = dict(color="#3498DB", weight=3, fillColor="#3498DB", fillOpacity=0.4)               # estilo Wind

        try:                                                                                         # intentar construir GeoJSON en memoria
            if ext == ".json":                                                                       # caso GeoJSON directo
                with open(path, "r", encoding="utf-8") as f:                                         # abrir fichero json
                    geo = json.load(f)                                                               # cargar a dict
            elif ext == ".parquet":                                                                  # caso Parquet -> GeoJSON
                geo = _to_geojson_from_parquet(path)                                                 # convertir parquet a GeoJSON dict
            else:                                                                                    # extensión no soportada
                return []                                                                            # no pintamos nada

            # proteger contra colecciones vacías para evitar zoom no deseado                        
            if not isinstance(geo, dict) or not geo.get("features"):                                 
                return []                                                                            

            layer = dl.GeoJSON(                                                                      # crear capa GeoJSON
                data=geo,                                                                            # pasar dict geojson
                zoomToBounds=True,                                                                   # ajustar mapa al contenido
                options=dict(style=style),                                                           # estilo para polígonos/líneas
                id=f"vessel-upload-{data.get('ts', 0)}"                                                # id único por timestamp
            )
            return [layer]                                                                           # devolver lista con la capa
        except Exception:                                                                             
            return []

    # Si el fichero no tiene la extension que queremos escribimos que no es valido, si es valido se guarda y se convierte a GeoJSON para ponerlo en el mapa (DEFENCE):
    @app.callback(
        Output("defence-file-label", "children", allow_duplicate=True),
        Output("defence-file", "className", allow_duplicate=True),
        Output("defence-file-store", "data", allow_duplicate=True),
        Input("defence-file", "filename"),
        Input("defence-file", "contents"),
        State("defence-file-store", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def on_upload_defence(filename, contents, prev_store, sid):
        if not filename:
            raise PreventUpdate
        label_text = filename
        if not _valid_ext(filename):
            return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}
        if not contents:
            return label_text, BASE_UPLOAD_CLASS, no_update
        try:
            sid = sid if isinstance(sid, str) and sid else None
            out_path = _save_upload_to_disk(contents, filename, "defence", sid)
            # eliminar fichero previo de ESTA sesión si existía
            try:
                if isinstance(prev_store, dict) and prev_store.get("valid"):
                    old_path = prev_store.get("path")
                    if old_path and Path(old_path).exists() and sid in Path(old_path).parts:
                        Path(old_path).unlink(missing_ok=True)
            except Exception:
                pass
            payload = {
                "valid": True,
                "kind": "defence",
                "filename": filename,
                "ext": os.path.splitext(filename)[1].lower(),
                "path": out_path,
                "ts": int(time.time()),
                "sid": sid
            }
            return label_text, BASE_UPLOAD_CLASS, payload
        except Exception as e:
            return f"{filename} — error: {e}", INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}
        
    

    # Sincronizos la UI para que si hay un fichero subido por el usuario se deshabiliten el boton DRAW y el Upload, limpiar GeoJSON al deseleccionar checklist, restaurar texto del Upload, etc. (DEFENCE)
    @app.callback(                                                                                              
        Output("defence-draw", "disabled", allow_duplicate=True),                                            
        Output("defence-file", "disabled", allow_duplicate=True),                                             
        Output("mgmt-defence", "children", allow_duplicate=True),                                                  
        Output("defence-file-store", "data", allow_duplicate=True),                                                
        Output("mgmt-defence-upload", "children", allow_duplicate=True),                                           
        Output("defence-file-label", "children", allow_duplicate=True),
        Output("defence-file", "filename", allow_duplicate=True),         # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("defence-file", "contents", allow_duplicate=True),                               # Anadido para que el usuario pueda seleccionar dos veces seguidas el mismo fichero
        Output("defence-file", "className"),                                     
        Input("defence-file-store", "data"),                                                                       
        Input("mgmt-defence", "children"),                                                                         
        Input("defence", "value"),                                                                            
        State("session-id", "data"),
        prevent_initial_call=True                                                                              
    )
    def sync_defence_ui(store, drawn_children, def_checked, sid):                                                
        selected = bool(def_checked)                                                                           
        file_present = isinstance(store, dict) and store.get("valid") is True                                   

        # Caso 1: checklist desmarcado -> limpiar Store y polígonos, y dejar controles deshabilitados            
        if not selected:
            # borrar toda la carpeta de la sesión para wind
            try:
                _rm_tree(_session_dir("defence", sid))
            except Exception:
                pass                                                                                             
            return True, True, [], None, [], "Choose json or parquet file", None, None, UPLOAD_CLASS                       

        # Caso 2: checklist marcado y hay fichero válido -> bloquear Draw y Upload                              
        if file_present:                                                                                         
            return True, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update               

        # Caso 3: checklist marcado -> habilitar Draw y Upload; si hay algo pintado se deshabilita el upload                                 
        has_drawn = (isinstance(drawn_children, list) and len(drawn_children) > 0) or bool(drawn_children) # Condicion para evaluar si hay un poligono pintado
        return False, has_drawn, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    


    # Callback que pinta el fichero en GeoJSON para los wind-farms (hacer lo mismo para las otras actividades y cambiar el color de los poligonos): (DEFENCE)
    @app.callback(                                                                                  
        Output("mgmt-defence-upload", "children"),                                                     # salida: capa pintada en el mapa
        Input("defence-file-store", "data"),                                                           # entrada: cambios en el Store de wind
        prevent_initial_call=True                                                                   
    )
    def paint_defence_uploaded(data):                                                                  
        if not data or not isinstance(data, dict):                                                  
            raise PreventUpdate                                                                      # no actualizar si no hay nada
        if not data.get("valid"):                                                                   
            return []                                                                                # limpiar capa si hubo intento inválido

        path = data.get("path")                                                                      # ruta del archivo guardado en la carpeta de la sesion
        ext  = (data.get("ext") or "").lower()                                                      

        # estilo común para polígonos/líneas (Leaflet aplicará estilo a features no puntuales)       
        style = dict(color="#e74c3c", weight=3, fillColor="#e74c3c", fillOpacity=0.4)               # estilo Wind

        try:                                                                                         # intentar construir GeoJSON en memoria
            if ext == ".json":                                                                       # caso GeoJSON directo
                with open(path, "r", encoding="utf-8") as f:                                         # abrir fichero json
                    geo = json.load(f)                                                               # cargar a dict
            elif ext == ".parquet":                                                                  # caso Parquet -> GeoJSON
                geo = _to_geojson_from_parquet(path)                                                 # convertir parquet a GeoJSON dict
            else:                                                                                    # extensión no soportada
                return []                                                                            # no pintamos nada

            # proteger contra colecciones vacías para evitar zoom no deseado                        
            if not isinstance(geo, dict) or not geo.get("features"):                                 
                return []                                                                            

            layer = dl.GeoJSON(                                                                      # crear capa GeoJSON
                data=geo,                                                                            # pasar dict geojson
                zoomToBounds=True,                                                                   # ajustar mapa al contenido
                options=dict(style=style),                                                           # estilo para polígonos/líneas
                id=f"defence-upload-{data.get('ts', 0)}"                                                # id único por timestamp
            )
            return [layer]                                                                           # devolver lista con la capa
        except Exception:                                                                             
            return []        

# -------------------------------------------- END LOGIC MANAGEMENT SCENARIOS DRAW AND UPLOAD ----------------------------------------------------------------------------------

# Callback to zoom to management area:
    @app.callback(  # centrar/zoom por área
        Output("map", "viewport", allow_duplicate=True),
        Output("mgmt-reset-button", "disabled"),
        Output("wind-farm", "options", allow_duplicate=True),
        Output("aquaculture", "options", allow_duplicate=True),
        Output("vessel", "options", allow_duplicate=True),
        Output("defence", "options", allow_duplicate=True),
        Input("mgmt-study-area-dropdown", "value"),
        State("wind-farm", "options"),
        State("aquaculture", "options"),
        State("vessel", "options"),
        State("defence", "options"),
        prevent_initial_call=True
    )
    def management_zoom(area, opts_w, opts_a, opts_v, opts_d):  # cambiar viewport
        if not area:
            raise PreventUpdate
        mapping = {
            "Santander": ([43.553269, -3.71836], 11),
            "North_Sea": ([51.824025,  2.627373], 9),
            "Irish_Sea": ([53.741164, -4.608093], 9),
            "Urdaibai_Estuary": ([43.364580815052316, -2.67957208131426804], 14),
            "Cadiz_Bay":        ([36.520874060327226, -6.203490800462997],  15)
        }
        center, zoom = mapping[area]
        new_opts_wind = [
            {**w, "disabled": False} if w.get("value") == "wind_farm" else w
            for w in (opts_w or [{"label":"Wind Farm","value":"wind_farm","disabled":True}])
        ]
        new_opts_aqua = [
            {**a, "disabled": False} if a.get("value") == "aquaculture" else a
            for a in (opts_a or [{"label":"Aquaculture","value":"aquaculture","disabled":True}])
        ]
        new_opts_vessel = [
            {**v, "disabled": False} if v.get("value") == "new_vessel_route" else v
            for v in (opts_v or [{"label":"New Vessel Route","value":"new_vessel_route","disabled":True}])
        ]
        new_opts_defence = [
            {**d, "disabled": False} if d.get("value") == "defence" else d
            for d in (opts_d or [{"label":"Defence","value":"defence","disabled":True}])
        ]

        return {"center": center, "zoom": zoom}, False, new_opts_wind, new_opts_aqua, new_opts_vessel, new_opts_defence
    
# Reset callback:
    @app.callback(
        Output("mgmt-study-area-dropdown", "value", allow_duplicate=True),
        Output("wind-farm", "value", allow_duplicate=True),
        Output("aquaculture", "value", allow_duplicate=True),
        Output("vessel", "value", allow_duplicate=True),
        Output("defence", "value", allow_duplicate=True),
        Output("map", "viewport", allow_duplicate=True),
        Output("mgmt-reset-button", "disabled", allow_duplicate=True),
        Output("wind-farm", "options", allow_duplicate=True),
        Output("aquaculture", "options", allow_duplicate=True),
        Output("vessel", "options", allow_duplicate=True),
        Output("defence", "options", allow_duplicate=True),
        Output("mgmt-table", "children", allow_duplicate=True),
        Output("mgmt-legend-affection", "hidden", allow_duplicate=True),
        Output("mgmt-info-button", "hidden", allow_duplicate=True),
        Output("mgmt-results", "hidden", allow_duplicate=True),
        Output("mgmt-scenarios-button", "hidden", allow_duplicate=True),
        Output("mgmt-current-button", "hidden", allow_duplicate=True),
        Input("mgmt-reset-button", "n_clicks"),
        State("wind-farm", "options"),
        State("aquaculture", "options"),
        State("vessel", "options"),
        State("defence", "options"),
        prevent_initial_call=True
    )
    def reset_mgmt(n, opts_w, opts_a, opts_v, opts_d):
        if not n:
            raise PreventUpdate

        default_view = {"center": [48.912724, -1.141208], "zoom": 6}

        # deshabilitar cada opción de nuevo
        new_opts_wind = [{**o, "disabled": True} if o.get("value") == "wind_farm" else o for o in (opts_w or [])]
        new_opts_aqua = [{**o, "disabled": True} if o.get("value") == "aquaculture" else o for o in (opts_a or [])]
        new_opts_vessel = [{**o, "disabled": True} if o.get("value") == "new_vessel_route" else o for o in (opts_v or [])]
        new_opts_defence = [{**o, "disabled": True} if o.get("value") == "defence" else o for o in (opts_d or [])]

        # limpiar selección, stores, etc. y volver a la configuracion inicial
        return (
            None,           # dropdown
            [], [], [], [], # values de los 4 checklists
            default_view,   # viewport
            True,           # deshabilitar botón reset
            new_opts_wind, new_opts_aqua, new_opts_vessel, new_opts_defence, [], True, True, True, True, True
        )
    
# Callback to enable run when any drawn or layer has a children:
    @app.callback(
        Output("mgmt-run-button", "disabled"),  # por si otro callback también lo toca
        Input("mgmt-wind", "children"),
        Input("mgmt-aquaculture", "children"),
        Input("mgmt-vessel", "children"),
        Input("mgmt-defence", "children"),
        Input("mgmt-wind-upload", "children"),
        Input("mgmt-aquaculture-upload", "children"),
        Input("mgmt-vessel-upload", "children"),
        Input("mgmt-defence-upload", "children"),
        prevent_initial_call=False  # evalúa también al cargar para dejarlo deshabilitado si está vacío
    )
    def toggle_mgmt_run(*children_groups):
        def has_items(c):                          # True si hay al menos un hijo
            if c is None:
                return False
            if isinstance(c, list):
                return len(c) > 0
            if isinstance(c, dict):               # un único componente serializado
                return True
            return bool(c)

        any_layer_has_data = any(has_items(c) for c in children_groups)
        return not any_layer_has_data             # disabled = no hay datos
    

# Callback to render the summary tabs:
    @app.callback(
        Output("mgmt-table", "children", allow_duplicate=True),
        Output("mgmt-legend-affection", "hidden"),
        Output("mgmt-info-button", "hidden"),
        Output("mgmt-results", "hidden"),
        Output("mgmt-scenarios-button", "hidden", allow_duplicate=True),
        Output("mgmt-scenarios-button", "disabled", allow_duplicate=True),
        Input("mgmt-run-button", "n_clicks"),
        State("mgmt-study-area-dropdown", "value"),
        prevent_initial_call=True
    )
    def render_mgmt_tabs(n, area):
        if not (n and area):
            raise PreventUpdate
        eunis_enabled = eunis_available(area)
        saltmarsh_enabled = saltmarsh_available(area)
        return _build_mgmt_tabs(eunis_enabled, saltmarsh_enabled), False, False, False, False, not saltmarsh_enabled

# Callback to compute the wind farm afection to eunis and saltmarshes:
    @app.callback(
        Output("mgmt-wind-eunis", "children"),
        Output("mgmt-wind-saltmarshes", "children"),
        Input("mgmt-table", "children"),
        State("mgmt-study-area-dropdown", "value"),
        State("mgmt-wind", "children"),
        State("mgmt-wind-upload", "children"),
        prevent_initial_call=True
    )
    def fill_wind_tabs(_tabs_ready, area, mgmt_w, mgmt_wu):
        if not _tabs_ready:
            raise PreventUpdate

        def render_table(df, empty_text):
            if df is None or df.empty:
                return html.Div(empty_text, className="text-muted", style={"padding":"8px"})
            table = dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in df.columns],
                data=df.to_dict("records"),
                sort_action="native", filter_action="native", page_action="none",
                style_table={"maxHeight":"720px","overflowY":"auto","border":"1px solid #ddd","borderRadius":"8px"},
                style_cell={"padding":"8px","fontSize":"1.0rem","textAlign":"center"},
                style_header={"fontWeight":"bold","backgroundColor":"#f7f7f7","borderBottom":"1px solid #ccc"},
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}]
            )
            return html.Div([html.Hr(), table], style={"marginTop":"8px"})

        # --- EUNIS (solo si está disponible para el área) ---
        if eunis_available(area):
            try:
                df_eu = activity_eunis_table(area, mgmt_w, mgmt_wu, label_col="AllcombD")
                eunis_div = render_table(df_eu, "No EUNIS habitats affected by Wind Farms.")
            except Exception:
                import traceback; traceback.print_exc()
                eunis_div = html.Div("Couldn't build EUNIS table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            eunis_div = html.Div("EUNIS data not available for this area.", className="text-muted", style={"padding":"8px"})

        # --- SALTMARSH (solo si está disponible para el área) ---
        if saltmarsh_available(area):
            try:
                df_sm = activity_saltmarsh_table(area, mgmt_w, mgmt_wu)
                saltmarsh_div = render_table(df_sm, "No saltmarshes and mudflats affected by Wind Farms.")
            except Exception:
                import traceback; traceback.print_exc()
                saltmarsh_div = html.Div("Couldn't build saltmarsh table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            # El subtab estará disabled; aún así devolvemos un placeholder inocuo
            saltmarsh_div = html.Div("Saltmarsh layers not available for this area.", className="text-muted", style={"padding":"8px"})

        return eunis_div, saltmarsh_div


# Callback to compute the aquaculture affection to eunis and saltmarshes:    
    @app.callback(
        Output("mgmt-aquaculture-eunis", "children"),
        Output("mgmt-aquaculture-saltmarshes", "children"),
        Input("mgmt-table", "children"),
        State("mgmt-study-area-dropdown", "value"),
        State("mgmt-aquaculture", "children"),
        State("mgmt-aquaculture-upload", "children"),
        prevent_initial_call=True
    )
    def fill_aquaculture_tabs(_tabs_ready, area, mgmt_a, mgmt_au):
        if not _tabs_ready:
            raise PreventUpdate

        def render_table(df, empty_text):
            if df is None or df.empty:
                return html.Div(empty_text, className="text-muted", style={"padding":"8px"})
            table = dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in df.columns],
                data=df.to_dict("records"),
                sort_action="native", filter_action="native", page_action="none",
                style_table={"maxHeight":"720px","overflowY":"auto","border":"1px solid #ddd","borderRadius":"8px"},
                style_cell={"padding":"8px","fontSize":"1.0rem","textAlign":"center"},
                style_header={"fontWeight":"bold","backgroundColor":"#f7f7f7","borderBottom":"1px solid #ccc"},
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}]
            )
            return html.Div([html.Hr(), table], style={"marginTop":"8px"})

        # --- EUNIS (solo si está disponible para el área) ---
        if eunis_available(area):
            try:
                df_eu = activity_eunis_table(area, mgmt_a, mgmt_au, label_col="AllcombD")
                eunis_div = render_table(df_eu, "No EUNIS habitats affected by Aquaculture.")
            except Exception:
                import traceback; traceback.print_exc()
                eunis_div = html.Div("Couldn't build EUNIS table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            eunis_div = html.Div("EUNIS data not available for this area.", className="text-muted", style={"padding":"8px"})

        # --- SALTMARSH (solo si está disponible para el área) ---
        if saltmarsh_available(area):
            try:
                df_sm = activity_saltmarsh_table(area, mgmt_a, mgmt_au)
                saltmarsh_div = render_table(df_sm, "No saltmarshes and mudflats affected by Aquaculture.")
            except Exception:
                import traceback; traceback.print_exc()
                saltmarsh_div = html.Div("Couldn't build saltmarsh table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            # El subtab estará disabled; aún así devolvemos un placeholder inocuo
            saltmarsh_div = html.Div("Saltmarsh layers not available for this area.", className="text-muted", style={"padding":"8px"})

        return eunis_div, saltmarsh_div

    
# Callback to compute the vessel route affection to eunis and saltmarshes:    
    @app.callback(
        Output("mgmt-vessel-eunis", "children"),
        Output("mgmt-vessel-saltmarshes", "children"),
        Input("mgmt-table", "children"),
        State("mgmt-study-area-dropdown", "value"),
        State("mgmt-vessel", "children"),
        State("mgmt-vessel-upload", "children"),
        prevent_initial_call=True
    )
    def fill_vessel_tabs(_tabs_ready, area, mgmt_v, mgmt_vu):
        if not _tabs_ready:
            raise PreventUpdate

        def render_table(df, empty_text):
            if df is None or df.empty:
                return html.Div(empty_text, className="text-muted", style={"padding":"8px"})
            table = dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in df.columns],
                data=df.to_dict("records"),
                sort_action="native", filter_action="native", page_action="none",
                style_table={"maxHeight":"720px","overflowY":"auto","border":"1px solid #ddd","borderRadius":"8px"},
                style_cell={"padding":"8px","fontSize":"1.0rem","textAlign":"center"},
                style_header={"fontWeight":"bold","backgroundColor":"#f7f7f7","borderBottom":"1px solid #ccc"},
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}]
            )
            return html.Div([html.Hr(), table], style={"marginTop":"8px"})

        # --- EUNIS (solo si está disponible para el área) ---
        if eunis_available(area):
            try:
                df_eu = activity_eunis_table(area, mgmt_v, mgmt_vu, label_col="AllcombD")
                eunis_div = render_table(df_eu, "No EUNIS habitats affected by New Vessel Routes.")
            except Exception:
                import traceback; traceback.print_exc()
                eunis_div = html.Div("Couldn't build EUNIS table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            eunis_div = html.Div("EUNIS data not available for this area.", className="text-muted", style={"padding":"8px"})

        # --- SALTMARSH (solo si está disponible para el área) ---
        if saltmarsh_available(area):
            try:
                df_sm = activity_saltmarsh_table(area, mgmt_v, mgmt_vu)
                saltmarsh_div = render_table(df_sm, "No saltmarshes and mudflats affected by New Vessel Routes.")
            except Exception:
                import traceback; traceback.print_exc()
                saltmarsh_div = html.Div("Couldn't build saltmarsh table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            # El subtab estará disabled; aún así devolvemos un placeholder inocuo
            saltmarsh_div = html.Div("Saltmarsh layers not available for this area.", className="text-muted", style={"padding":"8px"})

        return eunis_div, saltmarsh_div
    
# Callback to compute the defence affection to eunis and saltmarshes:    
    @app.callback(
        Output("mgmt-defence-eunis", "children"),
        Output("mgmt-defence-saltmarshes", "children"),
        Input("mgmt-table", "children"),
        State("mgmt-study-area-dropdown", "value"),
        State("mgmt-defence", "children"),
        State("mgmt-defence-upload", "children"),
        prevent_initial_call=True
    )
    def fill_defence_tabs(_tabs_ready, area, mgmt_d, mgmt_du):
        if not _tabs_ready:
            raise PreventUpdate

        def render_table(df, empty_text):
            if df is None or df.empty:
                return html.Div(empty_text, className="text-muted", style={"padding":"8px"})
            table = dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in df.columns],
                data=df.to_dict("records"),
                sort_action="native", filter_action="native", page_action="none",
                style_table={"maxHeight":"720px","overflowY":"auto","border":"1px solid #ddd","borderRadius":"8px"},
                style_cell={"padding":"8px","fontSize":"1.0rem","textAlign":"center"},
                style_header={"fontWeight":"bold","backgroundColor":"#f7f7f7","borderBottom":"1px solid #ccc"},
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}]
            )
            return html.Div([html.Hr(), table], style={"marginTop":"8px"})

        # --- EUNIS (solo si está disponible para el área) ---
        if eunis_available(area):
            try:
                df_eu = activity_eunis_table(area, mgmt_d, mgmt_du, label_col="AllcombD")
                eunis_div = render_table(df_eu, "No EUNIS habitats affected by Defence.")
            except Exception:
                import traceback; traceback.print_exc()
                eunis_div = html.Div("Couldn't build EUNIS table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            eunis_div = html.Div("EUNIS data not available for this area.", className="text-muted", style={"padding":"8px"})

        # --- SALTMARSH (solo si está disponible para el área) ---
        if saltmarsh_available(area):
            try:
                df_sm = activity_saltmarsh_table(area, mgmt_d, mgmt_du)
                saltmarsh_div = render_table(df_sm, "No saltmarshes and mudflats affected by Defence.")
            except Exception:
                import traceback; traceback.print_exc()
                saltmarsh_div = html.Div("Couldn't build saltmarsh table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            # El subtab estará disabled; aún así devolvemos un placeholder inocuo
            saltmarsh_div = html.Div("Saltmarsh layers not available for this area.", className="text-muted", style={"padding":"8px"})

        return eunis_div, saltmarsh_div
    
    @app.callback(
        Output("mgmt-total-eunis", "children"),
        Output("mgmt-total-saltmarshes", "children"),
        Input("mgmt-table", "children"),
        State("mgmt-study-area-dropdown", "value"),
        State("mgmt-wind", "children"),
        State("mgmt-wind-upload", "children"),
        State("mgmt-aquaculture", "children"),
        State("mgmt-aquaculture-upload", "children"),
        State("mgmt-vessel", "children"),
        State("mgmt-vessel-upload", "children"),
        State("mgmt-defence", "children"),
        State("mgmt-defence-upload", "children"),
        prevent_initial_call=True
    )
    def fill_total_tabs(_tabs_ready, area, mgmt_w, mgmt_wu, mgmt_a, mgmt_au, mgmt_v, mgmt_vu, mgmt_d, mgmt_du):
        if not _tabs_ready:
            raise PreventUpdate
        
        # Sum all activities geometries for Total affection:
        def _as_list(x):
            if x is None:
                return []
            if isinstance(x, list):
                return x
            return [x]

        total_children = (_as_list(mgmt_w)  + _as_list(mgmt_a)  + _as_list(mgmt_v)  + _as_list(mgmt_d))
        total_upload_children = (_as_list(mgmt_wu) + _as_list(mgmt_au) + _as_list(mgmt_vu) + _as_list(mgmt_du))

        def render_table(df, empty_text):
            if df is None or df.empty:
                return html.Div(empty_text, className="text-muted", style={"padding":"8px"})
            table = dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in df.columns],
                data=df.to_dict("records"),
                sort_action="native", filter_action="native", page_action="none",
                style_table={"maxHeight":"720px","overflowY":"auto","border":"1px solid #ddd","borderRadius":"8px"},
                style_cell={"padding":"8px","fontSize":"1.0rem","textAlign":"center"},
                style_header={"fontWeight":"bold","backgroundColor":"#f7f7f7","borderBottom":"1px solid #ccc"},
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fafafa"}]
            )
            return html.Div([html.Hr(), table], style={"marginTop":"8px"})

        # --- EUNIS (solo si está disponible para el área) ---
        if eunis_available(area):
            try:
                # Compute statistics on the total geometries:
                df_eu = activity_eunis_table(area, total_children, total_upload_children, label_col="AllcombD")
                eunis_div = render_table(df_eu, "No EUNIS habitats affected by Wind Farms.")
            except Exception:
                import traceback; traceback.print_exc()
                eunis_div = html.Div("Couldn't build EUNIS table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            eunis_div = html.Div("EUNIS data not available for this area.", className="text-muted", style={"padding":"8px"})

        # --- SALTMARSH (solo si está disponible para el área) ---
        if saltmarsh_available(area):
            try:
                df_sm = activity_saltmarsh_table(area, total_children, total_upload_children)
                saltmarsh_div = render_table(df_sm, "No saltmarshes and mudflats affected by Wind Farms.")
            except Exception:
                import traceback; traceback.print_exc()
                saltmarsh_div = html.Div("Couldn't build saltmarsh table.", style={"color":"crimson","whiteSpace":"pre-wrap"})
        else:
            # El subtab estará disabled; aún así devolvemos un placeholder inocuo
            saltmarsh_div = html.Div("Saltmarsh layers not available for this area.", className="text-muted", style={"padding":"8px"})

        return eunis_div, saltmarsh_div

# Callback to create tabs of saltmarsh scenario affection:
    @app.callback(
        Output("mgmt-table", "children", allow_duplicate=True),
        Output("mgmt-scenarios-button", "hidden"),
        Output("mgmt-current-button", "hidden"),
        Input("mgmt-scenarios-button", "n_clicks"),
        State("mgmt-study-area-dropdown", "value"),
        State("mgmt-wind", "children"),
        State("mgmt-wind-upload", "children"),
        State("mgmt-aquaculture", "children"),
        State("mgmt-aquaculture-upload", "children"),
        State("mgmt-vessel", "children"),
        State("mgmt-vessel-upload", "children"),
        State("mgmt-defence", "children"),
        State("mgmt-defence-upload", "children"),
        prevent_initial_call=True
    )
    def satlmarsh_scenarios_activities(clicks, area,
                                    mgmt_w, mgmt_wu,
                                    mgmt_a, mgmt_au,
                                    mgmt_v, mgmt_vu,
                                    mgmt_d, mgmt_du):
        if not clicks or not area:
            raise PreventUpdate
        return _build_saltmarsh_scenarios_layout(
            area,
            mgmt_w, mgmt_wu,
            mgmt_a, mgmt_au,
            mgmt_v, mgmt_vu,
            mgmt_d, mgmt_du
        ), True, False
    
# Callback: volver a las tabs “Current”
    @app.callback(
        Output("mgmt-table", "children", allow_duplicate=True),
        Output("mgmt-scenarios-button", "hidden", allow_duplicate=True),
        Output("mgmt-current-button", "hidden", allow_duplicate=True),
        Input("mgmt-current-button", "n_clicks"),
        State("mgmt-study-area-dropdown", "value"),
        prevent_initial_call=True
    )
    def current_affection(n, area):
        if not (n and area):
            raise PreventUpdate

        eunis_enabled     = eunis_available(area)
        saltmarsh_enabled = saltmarsh_available(area)

        return (
            _build_mgmt_tabs(eunis_enabled, saltmarsh_enabled),  # reconstruye tabs originales
            False,  # muestro botón "Scenarios"
            True,   # oculto botón "Current"
            # opcional: not saltmarsh_enabled
        )
    
# Add management activity legend:
    @app.callback(
        Output("mgmt-legend-div", "hidden", allow_duplicate=True),
        Output("layers-btn", "disabled"),
        Input("tabs", "value"),
        prevent_initial_call=True
    )
    def clear_overlay_on_tab_change(tab_value):
        if tab_value == "tab-management":
            return False, False            # limpiar overlay al salir del tab
        else:
            return True, True
        
# Add LayerGroup with the additional information for management activities location selection.
    # @app.callback(
    #     Output("mgmt-layers-control", "children"),
    #     Output("mgmt-layers-control", "style"),
    #     Input("tabs", "value"),
    #     State("mgmt-layers-control", "children"),
    #     prevent_initial_call=False
    # )
    # def toggle_mgmt_layers(tab_value, current_children):
    #     if tab_value == "tab-management":
    #         overlays = [
    #             # Grupo 1: Human activities
    #             dl.Overlay(
    #                 name="Human activities", checked=False,
    #                 children=dl.LayerGroup([
    #                     dl.LayerGroup(id="mgmt-ha-1"),
    #                     dl.LayerGroup(id="mgmt-ha-2"),
    #                     # añade más capas del grupo aquí…
    #                 ])
    #             ),
    #             # Grupo 2: Fishery
    #             dl.Overlay(
    #                 name="Fishery", checked=False,
    #                 children=dl.LayerGroup([
    #                     dl.LayerGroup(id="mgmt-fish-effort"),
    #                     dl.LayerGroup(id="mgmt-fish-closures"),
    #                     # …
    #                 ])
    #             ),
    #             # Grupo 3: (otro)
    #             dl.Overlay(
    #                 name="Environmental", checked=False,
    #                 children=dl.LayerGroup([
    #                     dl.LayerGroup(id="mgmt-env-mpas"),
    #                     dl.LayerGroup(id="mgmt-env-habitats"),
    #                 ])
    #             ),
    #         ]
    #         return overlays, {}                # visible
    #     # al salir de management:
    #     return [], {"display": "none", 'pointer-events': 'none'}         # oculto y sin hijos


    @app.callback(
        Output("layer-menu", "className"),
        Input("layers-btn", "n_clicks"),
        prevent_initial_call=False
    )
    def toggle_layers_panel(n):
        base = "card shadow-sm position-absolute collapse"
        return f"{base} show" if (n or 0) % 2 == 1 else base
    
    @app.callback(
        Output("mgmt-ha-1", "children"),
        Output("mgmt-ha-2", "children"),
        Output("mgmt-fish-effort", "children"),
        Output("mgmt-fish-closures", "children"),
        Input("chk-human", "value"),
        Input("chk-fish", "value"),
        prevent_initial_call=False
    )
    def toggle_sub_layers(human_vals, fish_vals):
        active = set((human_vals or []) + (fish_vals or []))

        def on(layer_id, component):
            return [component] if layer_id in active else []

        return (
            on("mgmt-ha-1", dl.GeoJSON(id="ha1")),          # <-- tu capa
            on("mgmt-ha-2", dl.GeoJSON(id="ha2")),
            on("mgmt-fish-effort",   dl.GeoJSON(id="feff")),
            on("mgmt-fish-closures", dl.GeoJSON(id="fclo")),
        )
