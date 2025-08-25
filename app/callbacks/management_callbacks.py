# management_callbacks.py
import os, base64, uuid
import dash
from dash import Input, Output, State, no_update, html
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






# mapping de botones -> (layer_key, color)
COLOR = {
    "wind-farm-draw": ("wind",   "#f39c12"),
    "aquaculture-draw": ("aqua", "#18BC9C"),
    "vessel-draw": ("vessel",    "#3498DB"),
    "defence-draw": ("defence",  "#e74c3c"),
}








BASE_UPLOAD_CLASS = "upload-as-input form-control form-control-sm"                     # clase base del upload (para restaurar)
INVALID_UPLOAD_CLASS = BASE_UPLOAD_CLASS + " upload-invalid"                      

# Function to validate files and save data to disk:
def _valid_ext(filename: str) -> bool:                                                 # función para validar extensión
    if not filename:                                                                   # si no hay nombre
        return False                                                                   # no es válido
    lower = filename.lower()                                                           # normalizar a minúsculas
    return lower.endswith(".json") or lower.endswith(".parquet")                       # aceptar solo .json o .parquet

def _save_upload_to_disk(contents: str, filename: str, kind: str) -> str:              # función para guardar subida a disco
    if not contents or "," not in contents:                                            # validar cadena base64
        raise ValueError("Upload contents malformed")                                  # error si el formato es incorrecto
    header, b64 = contents.split(",", 1)                                               # separar cabecera y datos
    data = base64.b64decode(b64)                                                       # decodificar base64 a bytes
    ext = os.path.splitext(filename)[1].lower()                                        # obtener extensión con punto (en minúsculas)
    out_dir = os.path.join(os.getcwd(), "uploads", kind)                               # construir carpeta destino por actividad
    os.makedirs(out_dir, exist_ok=True)                                                # crear la carpeta si no existe
    out_path = os.path.join(out_dir, f"{uuid.uuid4().hex}{ext}")                       # construir nombre único de salida
    with open(out_path, "wb") as f:                                                    # abrir archivo en modo binario
        f.write(data)                                                                  # escribir bytes al disco
    return out_path


# def _session_dir(kind: str, session_id: str) -> str:                                  # construir carpeta de sesión
#     base = Path(os.getcwd()) / "uploads" / kind / (session_id or "anon")              # ruta base uploads/kind/sid
#     base.mkdir(parents=True, exist_ok=True)                                           # crear si no existe
#     return str(base)                                                                  # devolver como str

# def _rm_tree(path: str) -> None:                                                      # borrar árbol de forma segura
#     try:
#         if path and Path(path).exists():
#             shutil.rmtree(path, ignore_errors=True)                                   # borrar recursivo
#     except Exception:
#         pass

# def _estimate_b64_size(contents: str) -> int:                                         # estimar bytes del base64 (sin decodificar)
#     if not contents or "," not in contents:
#         return 0
#     b64 = contents.split(",", 1)[1]
#     # aproximación: cada 4 chars ~ 3 bytes
#     return int(len(b64) * 3 / 4)

# def _save_upload_to_disk(contents: str, filename: str, kind: str, session_id: str) -> str:  # guardar en carpeta de sesión
#     if not contents or "," not in contents:
#         raise ValueError("Upload contents malformed")
#     # límite de tamaño
#     size_bytes = _estimate_b64_size(contents)
#     header, b64 = contents.split(",", 1)
#     data = base64.b64decode(b64)
#     ext = os.path.splitext(filename)[1].lower()
#     out_dir = _session_dir(kind, session_id)
#     out_path = Path(out_dir) / f"{uuid.uuid4().hex}{ext}"
#     with open(out_path, "wb") as f:
#         f.write(data)
#     return str(out_path)







def _detect_lonlat_columns(df):                                   # detectar columnas lon/lat con nombres comunes
    cols = {c.lower(): c for c in df.columns}                     # map de minúsculas -> nombre original
    lon_candidates = ["lon", "longitude", "x"]                    # candidatos a longitud
    lat_candidates = ["lat", "latitude", "y"]                     # candidatos a latitud
    lon_col = next((cols[c] for c in lon_candidates if c in cols), None)  # primera coincidencia lon
    lat_col = next((cols[c] for c in lat_candidates if c in cols), None)  # primera coincidencia lat
    return lon_col, lat_col                                       # devolver nombres (o None)

def _df_to_feature_collection_from_points(df, lon_col, lat_col):  # construir FeatureCollection desde lon/lat
    feats = []                                                    # lista de features
    for _, row in df.dropna(subset=[lon_col, lat_col]).iterrows():# iterar por filas válidas
        try:                                                      # proteger la conversión numérica
            lon = float(row[lon_col])                             # convertir lon a float
            lat = float(row[lat_col])                             # convertir lat a float
        except Exception:                                         # si falla la conversión
            continue                                              # saltar fila
        props = row.drop([lon_col, lat_col]).to_dict()            # propiedades: resto de columnas
        feats.append({                                            # añadir feature
            "type": "Feature",                                    # tipo de entidad
            "geometry": {"type": "Point", "coordinates": [lon, lat]},  # punto GeoJSON
            "properties": props                                   # propiedades
        })
    return {"type": "FeatureCollection", "features": feats}       # devolver FeatureCollection

def _to_geojson_from_parquet(path):                               # convertir parquet a GeoJSON (dict)
    # 1) Intentar leer como GeoParquet con geopandas
    if gpd is not None:                                           # si geopandas está disponible
        try:                                                      # intentar leer con geopandas
            gdf = gpd.read_parquet(path)                          # leer parquet geoespacial
            if gdf.empty:                                         # si está vacío
                return {"type": "FeatureCollection", "features": []}  # colección vacía
            if gdf.crs is not None:                               # si viene con CRS
                try:                                              # intentar reproyectar a WGS84
                    gdf = gdf.to_crs(4326)                        # reproyectar a EPSG:4326
                except Exception:                                 # si falla reproyección
                    pass                                          # continuar con geometría original
            geojson = json.loads(gdf.to_json())                   # convertir a GeoJSON (dict)
            return geojson                                        # devolver dict
        except Exception:                                         # si falla geopandas
            pass                                                  # continuar con plan B

    # 2) Plan B: pandas + heurísticas (WKT, WKB, lon/lat)
    df = pd.read_parquet(path)                                    # leer parquet con pandas
    if df.empty:                                                  # si está vacío
        return {"type": "FeatureCollection", "features": []}      # devolver vacío

    lower_cols = {c.lower(): c for c in df.columns}               # map de minúsculas -> original
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
        return _df_to_feature_collection_from_points(df, lon_col, lat_col)  # construir FeatureCollection

    # 2.d) si no se pudo inferir geometría, devolver vacío
    return {"type": "FeatureCollection", "features": []}          # devolver vacío si no hay geometría detectable











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

    












    # @app.callback(                                                                            # crear session-id si no existe
    #     Output("welcome-store", "data"),
    #     Input("tabs", "value"),
    #     State("session-id", "data"),
    #     prevent_initial_call=False
    # )
    # def ensure_session_id(_active_tab, sid):
    #     if sid:
    #         raise PreventUpdate
    #     return uuid.uuid4().hex



    # --- SUBIDA WIND: validar extensión, guardar a disco y rellenar el Store ---
    @app.callback(                                                                                 # registrar callback en la instancia app
        Output("wind-farm-file-label", "children", allow_duplicate=True),                          # actualizar texto del “input” (siempre mostrar el nombre)
        Output("wind-farm-file", "className", allow_duplicate=True),                               # aplicar clase roja si inválido
        Output("wind-file-store", "data", allow_duplicate=True),                                   # guardar metadatos/ruta en Store                                                                                                    
        Input("wind-farm-file", "filename"),                                                       # nombre de archivo seleccionado
        Input("wind-farm-file", "contents"),                                                       # contenido base64 del archivo
        prevent_initial_call=True                                                                  # no ejecutar en la carga inicial
    )
    def on_upload_wind(filename, contents):                                                        # manejador de subida para Wind
        if not filename:                                                                           # si no hay nombre (no se ha subido nada)
            raise PreventUpdate                                                                    # no actualizar salidas

        # 1) SIEMPRE mostrar el nombre que acaba de elegir el usuario (válido o no)                # comentario
        label_text = filename                                                                       # guardar el texto del label

        # 2) Si la extensión no es válida -> pintamos rojo y no tocamos el Store (o lo marcamos inválido)
        if not _valid_ext(filename):                                                                # validar extensión .json/.parquet
            return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}    # pintar rojo y store inválido

        # 3) Extensión válida pero aún no llegaron los contenidos -> mostrar nombre y esperar base64
        if not contents:                                                                            # si aún no llegó el base64
            return label_text, BASE_UPLOAD_CLASS, no_update                                         # mostrar nombre y esperar contents

        # 4) Guardar a disco y rellenar store
        try:                                                                                        # intentar guardar a disco
            out_path = _save_upload_to_disk(contents, filename, "wind")                             # escribir en ./uploads/wind/<uuid>.<ext>
            payload = {                                                                             # construir payload para Store
                "valid": True,                                                                      # flag de validez
                "kind": "wind",                                                                     # tipo de actividad
                "filename": filename,                                                               # nombre original
                "ext": os.path.splitext(filename)[1].lower(),                                       # extensión en minúsculas
                "path": out_path,                                                                   # ruta absoluta del archivo en disco
                "ts": int(time.time())                                                              # timestamp útil para invalidar caché
            }
            return label_text, BASE_UPLOAD_CLASS, payload                                           # restaurar clase base y guardar Store
        except Exception as e:                                                                       # capturar error de escritura
            err_label = f"{filename} — error saving: {e}"                                           # mensaje de error
            return err_label, INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}              # marcar rojo y Store inválido



    # @app.callback(
    #     Output("wind-farm-file-label", "children", allow_duplicate=True),
    #     Output("wind-farm-file", "className", allow_duplicate=True),
    #     Output("wind-file-store", "data", allow_duplicate=True),
    #     Input("wind-farm-file", "filename"),
    #     Input("wind-farm-file", "contents"),
    #     State("wind-file-store", "data"),
    #     State("welcome-store", "data"),
    #     prevent_initial_call=True
    # )
    # def on_upload_wind(filename, contents, prev_store, sid):
    #     if not filename:
    #         raise PreventUpdate
    #     label_text = filename
    #     if not _valid_ext(filename):
    #         return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}
    #     if not contents:
    #         return label_text, BASE_UPLOAD_CLASS, no_update
    #     try:
    #         out_path = _save_upload_to_disk(contents, filename, "wind", sid)
    #         # eliminar fichero previo de ESTA sesión si existía
    #         try:
    #             if isinstance(prev_store, dict) and prev_store.get("valid"):
    #                 old_path = prev_store.get("path")
    #                 if old_path and Path(old_path).exists() and sid in Path(old_path).parts:
    #                     Path(old_path).unlink(missing_ok=True)
    #         except Exception:
    #             pass
    #         payload = {
    #             "valid": True,
    #             "kind": "wind",
    #             "filename": filename,
    #             "ext": os.path.splitext(filename)[1].lower(),
    #             "path": out_path,
    #             "ts": int(time.time()),
    #             "sid": sid
    #         }
    #         return label_text, BASE_UPLOAD_CLASS, payload
    #     except Exception as e:
    #         return f"{filename} — error: {e}", INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}


    # --- SINCRONIZACIÓN UI WIND: bloquear/ desbloquear Draw y Upload según Store, y limpiar al desmarcar ---  # explicación de bloque
    @app.callback(                                                                                              # registrar callback en Dash
        Output("wind-farm-draw", "disabled", allow_duplicate=True),                                             # salida: deshabilitar/habilitar botón Draw
        Output("wind-farm-file", "disabled", allow_duplicate=True),                                             # salida: deshabilitar/habilitar Upload
        Output("mgmt-wind", "children", allow_duplicate=True),                                                  # salida: limpiar polígonos dibujados si procede
        Output("wind-file-store", "data", allow_duplicate=True),                                                # salida: limpiar Store si procede
        Output("mgmt-wind-upload", "children", allow_duplicate=True),                                           # salida: limpiar capa de datos subidos si procede
        Output("wind-farm-file-label", "children", allow_duplicate=True),                                      # salida: restaurar texto del label si procede
        Input("wind-file-store", "data"),                                                                       # entrada: cambios en Store (subida de fichero)
        Input("mgmt-wind", "children"),                                                                         # entrada: cambios en el FeatureGroup de Draw (escucha, no decide)
        Input("wind-farm", "value"),                                                                            # entrada: estado del checklist (marcado / desmarcado)
        prevent_initial_call=True                                                                               # no ejecutar en la carga inicial
    )
    def sync_wind_ui(store, drawn_children, wind_checked):                                                      # función que sincroniza la UI
        selected = bool(wind_checked)                                                                           # true si el checklist está marcado
        file_present = isinstance(store, dict) and store.get("valid") is True                                   # true si hay fichero válido en el Store

        # Caso 1: checklist desmarcado -> limpiar Store y polígonos, y dejar controles deshabilitados            # comentario
        if not selected:                                                                                         # si la actividad no está seleccionada
            return True, True, [], None, [], "Choose file: .json or .parquet"                                    # deshabilitar controles, vaciar draw y store

        # Caso 2: checklist marcado y hay fichero válido -> bloquear Draw y Upload                               # comentario
        if file_present:                                                                                         # si existe un archivo válido en el store
            return True, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update                    # bloquear controles, no tocar draw ni store

        # Caso 3: checklist marcado y NO hay fichero -> habilitar Draw y Upload                                  # comentario
        return False, False, dash.no_update, dash.no_update, dash.no_update, dash.no_update                      # habilitar controles, no tocar draw ni store


    # @app.callback(
    #     Output("wind-farm-draw", "disabled", allow_duplicate=True),
    #     Output("wind-farm-file", "disabled", allow_duplicate=True),
    #     Output("mgmt-wind", "children", allow_duplicate=True),
    #     Output("wind-file-store", "data", allow_duplicate=True),
    #     Input("wind-file-store", "data"),
    #     Input("mgmt-wind", "children"),
    #     Input("wind-farm", "value"),
    #     State("session-id", "data"),
    #     prevent_initial_call=True
    # )
    # def sync_wind_ui(store, drawn_children, wind_checked, sid):
    #     selected = bool(wind_checked)
    #     file_present = isinstance(store, dict) and store.get("valid") is True

    #     if not selected:
    #         # borrar toda la carpeta de la sesión para wind
    #         try:
    #             _rm_tree(_session_dir("wind", sid))
    #         except Exception:
    #             pass
    #         return True, True, [], None

    #     if file_present:
    #         return True, True, no_update, no_update

    #     return False, False, no_update, no_update



    @app.callback(                                                                                  # registrar callback
        Output("mgmt-wind-upload", "children"),                                                     # salida: capa pintada en el mapa
        Input("wind-file-store", "data"),                                                           # entrada: cambios en el Store de wind
        prevent_initial_call=True                                                                   # no ejecutar al inicio
    )
    def paint_wind_uploaded(data):                                                                  # función de pintado
        if not data or not isinstance(data, dict):                                                  # validar estructura del store
            raise PreventUpdate                                                                      # no actualizar si no hay nada
        if not data.get("valid"):                                                                   # si no es válido
            return []                                                                                # limpiar capa si hubo intento inválido

        path = data.get("path")                                                                      # ruta del archivo subido
        ext  = (data.get("ext") or "").lower()                                                      # extensión en minúsculas

        # estilo común para polígonos/líneas (Leaflet aplicará estilo a features no puntuales)       # comentario
        style = dict(color="#f39c12", weight=3, fillColor="#f39c12", fillOpacity=0.4)               # estilo Wind

        try:                                                                                         # intentar construir GeoJSON en memoria
            if ext == ".json":                                                                       # caso GeoJSON directo
                with open(path, "r", encoding="utf-8") as f:                                         # abrir fichero json
                    geo = json.load(f)                                                               # cargar a dict
            elif ext == ".parquet":                                                                  # caso Parquet -> GeoJSON
                geo = _to_geojson_from_parquet(path)                                                 # convertir parquet a GeoJSON dict
            else:                                                                                    # extensión no soportada
                return []                                                                            # no pintamos nada

            # proteger contra colecciones vacías para evitar zoom no deseado                        # comentario
            if not isinstance(geo, dict) or not geo.get("features"):                                 # si no hay features
                return []                                                                            # no pintamos

            layer = dl.GeoJSON(                                                                      # crear capa GeoJSON
                data=geo,                                                                            # pasar dict geojson
                zoomToBounds=True,                                                                   # ajustar mapa al contenido
                options=dict(style=style),                                                           # estilo para polígonos/líneas
                id=f"wind-upload-{data.get('ts', 0)}"                                                # id único por timestamp
            )
            return [layer]                                                                           # devolver lista con la capa
        except Exception:                                                                             # si algo falla (parseo/IO)
            return []                                                                                # no pintar para no romper la app



