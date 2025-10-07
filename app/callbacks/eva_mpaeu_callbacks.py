import dash, json, time, os, sys #traceback
from dash import Input, Output, State, no_update, html, dcc, ALL, ctx
from dash.exceptions import PreventUpdate
from pathlib import Path
import geopandas as gpd
import pandas as pd
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from shapely import wkt as shp_wkt  
from shapely import wkb as shp_wkb
from shapely.geometry import mapping

from app.callbacks.management_callbacks import _valid_ext, _save_upload_to_disk, _to_geojson_from_parquet, _detect_lonlat_columns, _df_to_feature_collection_from_polygon, _estimate_b64_size, _rm_tree, _session_dir

# Classes:
COLOR = {"eva-overscale-sa-draw": ("study-area",   "#015B97")}
UPLOAD_CLASS = "form-control form-control-lg"
BASE_UPLOAD_CLASS = "form-control is-valid form-control-lg"               
INVALID_UPLOAD_CLASS = "form-control is-invalid form-control-lg"  

# Utility functions:
def _parse_csv_ints(text: str):
    if not text:
        return []
    items = [t.strip() for t in text.replace(";", ",").split(",")]
    out = []
    for t in items:
        if not t:
            continue
        try:
            out.append(int(t))
        except ValueError:
            pass
    return out

def _none_if_empty(v):
    return None if v in ("", None) else v

def _get_prop(node, key, default=None):
    return (node or {}).get("props", {}).get(key, default)

def _has_any_child(children) -> bool:
    """True if at least one children"""
    if children is None:
        return False
    if isinstance(children, (list, tuple)):
        return any(ch is not None for ch in children)
    return True

# Check if group configuration is complete:
def _is_group_complete(cfg: dict) -> bool:
    if not cfg:
        return False

    if not cfg.get("name"): return False
    if not cfg.get("eez_country"): return False
    if cfg.get("eez_grid_size") in (None, ""): return False

    lrf = cfg.get("lrf", {}) or {}
    nrf = cfg.get("nrf", {}) or {}

    lrf_ids = lrf.get("taxon_ids") or []
    nrf_ids = nrf.get("taxon_ids") or []
    esf_ids = cfg.get("esf_taxon_ids") or []
    hfsbh_ids = cfg.get("hfsbh_taxon_ids") or []
    mss_ids = cfg.get("mss_taxon_ids") or []

    any_list = any([lrf_ids, nrf_ids, esf_ids, hfsbh_ids, mss_ids])
    if not any_list:
        return False

    if lrf_ids and lrf.get("threshold_pct") in (None, ""):
        return False
    if nrf_ids and nrf.get("threshold_pct") in (None, ""):
        return False

    return True






def _to_leaflet_polys(geojson):
    """Convierte Polygon/MultiPolygon GeoJSON -> lista de dl.Polygon(positions=...)."""
    feats = (geojson or {}).get("features", [])
    comps = []

    def lonlat_to_latlon(coords):
        # GeoJSON [lon,lat] -> Leaflet [lat,lon]
        return [[lat, lon] for lon, lat in coords]

    for f in feats:
        g = (f or {}).get("geometry") or {}
        gtype = g.get("type")
        if gtype == "Polygon":
            ring = g.get("coordinates", [[]])[0]
            comps.append(dl.Polygon(positions=lonlat_to_latlon(ring),
                                    color="#0d6efd", fillColor="#0d6efd",
                                    fillOpacity=0.35, weight=3))
        elif gtype == "MultiPolygon":
            for poly in g.get("coordinates", []):
                ring = poly[0] if poly else []
                comps.append(dl.Polygon(positions=lonlat_to_latlon(ring),
                                        color="#0d6efd", fillColor="#0d6efd",
                                        fillOpacity=0.35, weight=3))
        # otros tipos: ignorar
    return comps

# Main Callback function:
def register_eva_mpaeu_callbacks(app: dash.Dash):

        @app.callback(
            Output("fg-button-container", "children"),
            Output("fg-button-tooltips", "children"),
            Input("add-functional-group", "n_clicks"),
            State("fg-button-container", "children"),
            State("fg-button-tooltips", "children"),
            prevent_initial_call=True
        )
        def add_functional_group(n_clicks, button_children, tooltip_children):
            if not n_clicks:
                raise PreventUpdate

            button_children = button_children or []
            tooltip_children = tooltip_children or []

            i = len(button_children) + 1
            btn_id = {"type": "fg-button", "index": i}

            button_children.append(
                html.Button(
                    f"Group {i}",
                    id=btn_id,
                    n_clicks=0,
                    className="btn btn-outline-primary w-100"
                )
            )

            tooltip_children.append(
                dbc.Tooltip(
                    f"Group {i} configuration",
                    target=btn_id,              
                    placement="bottom"
                )
            )

            return button_children, tooltip_children
        
        @app.callback(
            Output("fg-config-modal", "is_open", allow_duplicate=True),
            Output("fg-modal-title", "children"),
            Output("fg-selected-index", "data", allow_duplicate= True),
            Output("fg-last-click-ts", "data", allow_duplicate=True),  # actualizar el último timestamp usado
            Input({"type": "fg-button", "index": ALL}, "n_clicks_timestamp"),
            Input("add-functional-group", "n_clicks"),   # para poder ignorar su trigger
            State("fg-last-click-ts", "data"),
            prevent_initial_call=True
        )
        def open_modal(ts_list, add_cnt, last_ts):
            # Si el trigger fue el botón de añadir → ignorar
            if hasattr(ctx, "triggered_id"):
                if ctx.triggered_id == "add-functional-group":
                    raise PreventUpdate
            else:
                prop_id = (ctx.triggered[0]["prop_id"] if ctx.triggered else "")
                if prop_id.startswith("add-functional-group."):
                    raise PreventUpdate

            if not ts_list or all((t or 0) == 0 for t in ts_list):
                raise PreventUpdate

            # Buscar el botón realmente clicado más recientemente
            ts_list = [(t or 0) for t in ts_list]
            max_ts = max(ts_list)
            if max_ts <= (last_ts or 0):
                raise PreventUpdate

            # Index
            idx0 = ts_list.index(max_ts)
            i = idx0 + 1

            return True, f"Configure Group {i}", i, max_ts

        @app.callback(
            Output("fg-configs", "data", allow_duplicate=True),
            Output("fg-config-modal", "is_open", allow_duplicate=True),         # cerrar modal
            Output("fg-button-container", "children", allow_duplicate=True),    # renombrar botón
            Output("fg-button-tooltips", "children", allow_duplicate=True),     # actualizar tooltip
            Input("fg-modal-save", "n_clicks"),
            State("fg-selected-index", "data"),
            State("fg-configs", "data"),
            State("fg-input-name", "value"),
            State("fg-input-eez", "value"),
            State("fg-input-eez-grid-size", "value"),
            State("fg-lrf-taxonid", "value"),
            State("fg-lrf-threshold", "value"),
            State("fg-nrf-taxonid", "value"),
            State("fg-nrf-threshold", "value"),
            State("fg-esf-taxonid", "value"),
            State("fg-hfsbh-taxonid", "value"),
            State("fg-mss-taxonid", "value"),
            State("fg-button-container", "children"),
            State("fg-button-tooltips", "children"),
            prevent_initial_call=True
        )
        def save_group_config(n_save, idx, data,
                            name, eez, eez_grid,
                            lrf_ids, lrf_thr, nrf_ids, nrf_thr,
                            esf_ids, hfsbh_ids, mss_ids,
                            btn_children, tip_children):
            if not n_save or not idx:
                raise PreventUpdate

            data = data or {}
            key = str(idx)

            cfg = {
                "name": _none_if_empty(name),
                "eez_country": _none_if_empty(eez),
                "eez_grid_size": eez_grid if eez_grid is not None else None,
                "lrf": {"taxon_ids": _parse_csv_ints(lrf_ids), "threshold_pct": lrf_thr if lrf_thr is not None else None},
                "nrf": {"taxon_ids": _parse_csv_ints(nrf_ids), "threshold_pct": nrf_thr if nrf_thr is not None else None},
                "esf_taxon_ids": _parse_csv_ints(esf_ids),
                "hfsbh_taxon_ids": _parse_csv_ints(hfsbh_ids),
                "mss_taxon_ids": _parse_csv_ints(mss_ids),
            }
            data[key] = cfg

            # ---- Rename button and tooltip with the group name configuration ----
            btn_children = btn_children or []
            tip_children = tip_children or []
            new_label = f"Group {idx}" + (f" – {name}" if name else "")

            # Button
            for k, child in enumerate(btn_children):
                cid = _get_prop(child, "id")
                if isinstance(cid, dict) and cid.get("type") == "fg-button" and cid.get("index") == idx:
                    n_clicks = _get_prop(child, "n_clicks", 0)
                    className = _get_prop(child, "className", "btn btn-outline-primary w-100")
                    btn_children[k] = html.Button(
                        new_label,
                        id=cid,
                        n_clicks=n_clicks,
                        className=className
                    )
                    break

            # Tooltip
            for k, tip in enumerate(tip_children):
                target = _get_prop(tip, "target")
                if target == {"type": "fg-button", "index": idx}:
                    placement = _get_prop(tip, "placement", "bottom")
                    tip_children[k] = dbc.Tooltip(
                        f"Configure {new_label}",
                        target=target,
                        placement=placement
                    )
                    break

            return data, False, btn_children, tip_children
        
        @app.callback(
            Output("fg-input-name", "value", allow_duplicate=True),
            Output("fg-input-eez", "value", allow_duplicate=True),
            Output("fg-input-eez-grid-size", "value", allow_duplicate=True),
            Output("fg-lrf-taxonid", "value", allow_duplicate=True),
            Output("fg-lrf-threshold", "value", allow_duplicate=True),
            Output("fg-nrf-taxonid", "value", allow_duplicate=True),
            Output("fg-nrf-threshold", "value", allow_duplicate=True),
            Output("fg-esf-taxonid", "value", allow_duplicate=True),
            Output("fg-hfsbh-taxonid", "value", allow_duplicate=True),
            Output("fg-mss-taxonid", "value", allow_duplicate=True),
            Input("fg-selected-index", "data"),
            State("fg-configs", "data"),
            prevent_initial_call=True
        )
        def load_group_config(idx, data):
            if not idx:
                raise PreventUpdate
            cfg = (data or {}).get(str(idx), {})
            lrf = cfg.get("lrf", {})
            nrf = cfg.get("nrf", {})

            def csv(v): return "" if not v else ", ".join(map(str, v))

            return (
                cfg.get("name", ""),
                cfg.get("eez_country", ""),
                cfg.get("eez_grid_size", None),
                csv(lrf.get("taxon_ids")),
                lrf.get("threshold_pct", None),
                csv(nrf.get("taxon_ids")),
                nrf.get("threshold_pct", None),
                csv(cfg.get("esf_taxon_ids")),
                csv(cfg.get("hfsbh_taxon_ids")),
                csv(cfg.get("mss_taxon_ids")),
            )


        @app.callback(
            Output("fg-config-modal", "is_open"),
            Input("fg-modal-close", "n_clicks"),
            Input("fg-modal-save", "n_clicks"),
            State("fg-config-modal", "is_open"),
            prevent_initial_call=True
        )
        def close_modal(n_close, n_save, is_open):
            if not is_open:
                raise PreventUpdate
            return False
        
        @app.callback(
            Output("fg-button-container", "children", allow_duplicate=True),
            Input("fg-configs", "data"),
            State("fg-button-container", "children"),
            prevent_initial_call=True
        )
        def colorize_group_buttons(cfgs, btn_children):
            btn_children = btn_children or []
            cfgs = cfgs or {}

            new_children = []
            for child in btn_children:
                cid = _get_prop(child, "id")
                if isinstance(cid, dict) and cid.get("type") == "fg-button":
                    idx = cid.get("index")
                    cfg = cfgs.get(str(idx), {})
                    complete = _is_group_complete(cfg)

                    label = _get_prop(child, "children", f"Group {idx}")
                    n_clicks = _get_prop(child, "n_clicks", 0)

                    className = "btn w-100 "
                    className += "btn-outline-success" if complete else "btn-outline-danger"

                    new_children.append(
                        html.Button(
                            label,
                            id=cid,
                            n_clicks=n_clicks,
                            className=className.strip()
                        )
                    )
                else:
                    new_children.append(child)

            return new_children
        
        # Callback to get Assessment grid radio option:
        @app.callback(
            Output("eva-overscale-h3-level", "disabled", allow_duplicate=True),
            Output("eva-overscale-quadrat-size", "disabled", allow_duplicate=True),
            Input("opt-radio", "value"),
            prevent_initial_call = True
        )
        def toggle_inputs(opt):
            return (opt != "h3", opt != "quadrat")
        
        # Callback to send Assessment Grid size to store (and update Div to show the value):
        @app.callback(
            Output("ag-size-store", "data", allow_duplicate=True),
            Input("eva-overscale-h3-level", "value"),
            Input("eva-overscale-quadrat-size", "value"),
            Input("opt-radio", "value"),   # ← antes era State
            prevent_initial_call=True
        )
        def update_store_from_grid_inputs(h3_val, q_val, opt):
            selected = h3_val if opt == "h3" else q_val
            return {"type": opt, "h3": h3_val, "quadrat": q_val, "size": selected}
        
        # Callback to enable and disable Run button:
        @app.callback(
            Output("eva-overscale-run-button", "disabled", allow_duplicate=True),
            Input("fg-configs", "data"),
            Input("ag-size-store", "data"),
            Input("eva-overscale-draw", "children"),
            Input("eva-overscale-upload", "children"),
            State("fg-button-container", "children"),
            prevent_initial_call=True
        )
        def toggle_run_button(cfgs, ag, sa_draw, sa_upload, btn_children):
            # 1) Existing groups
            idxs = []
            for child in (btn_children or []):
                cid = _get_prop(child, "id")
                if isinstance(cid, dict) and cid.get("type") == "fg-button":
                    idxs.append(str(cid.get("index")))
            if not idxs:
                return True  # no hay grupos

            # 2) Valid Grid Size
            ag_ok = bool(ag) and ag.get("type") in ("h3", "quadrat") and ag.get("size") not in (None, "")
            if not ag_ok:
                return True

            # 3) ROI presente: draw o upload con al menos un hijo
            roi_ok = _has_any_child(sa_draw) or _has_any_child(sa_upload)
            if not roi_ok:
                return True

            # 4) Todos los grupos completos + ROI OK
            cfgs = cfgs or {}
            groups_ok = all(_is_group_complete(cfgs.get(i)) for i in idxs)
            all_complete = groups_ok and roi_ok

            return not all_complete
        
        # Callback to reset all:
        @app.callback(
            Output("fg-configs", "data"),
            Output("fg-selected-index", "data"),
            Output("fg-last-click-ts", "data"),
            Output("fg-button-container", "children", allow_duplicate=True),
            Output("fg-button-tooltips", "children", allow_duplicate=True),
            Output("opt-radio", "value"),
            Output("eva-overscale-h3-level", "value", allow_duplicate=True),
            Output("eva-overscale-quadrat-size", "value", allow_duplicate=True),
            Output("eva-overscale-h3-level", "disabled"),
            Output("eva-overscale-quadrat-size", "disabled"),
            Output("ag-size-store", "data"),
            Output("eva-overscale-run-button", "disabled"),
            Output("eva-overscale-draw", "children", allow_duplicate=True),
            Output("eva-overscale-sa-draw", "disabled", allow_duplicate=True),
            Output("eva-overscale-upload", "children", allow_duplicate=True),
            Output("eva-overscale-sa-file", "disabled", allow_duplicate=True),
            Output("eva-overscale-sa-file-label", "children"),
            Output("eva-overscale-file-store", "data"),
            Input("eva-overscale-reset-button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset_all(n):
            if not n:
                raise PreventUpdate
            return (
                {},           # fg-configs
                None,         # fg-selected-index
                0,            # fg-last-click-ts
                [],           # fg-button-container 
                [],           # fg-button-tooltips
                "h3",         # radio por default
                None,         # h3 value
                None,         # quadrat value
                False,        # h3 enabled
                True,         # quadrat disabled
                {},           # ag-size-store empty
                True,         # Run disabled
                [],           # Clear Study Area polygons Draw
                False,        # Enable Draw Button 
                [],           # Clear Study Area polygons uploaded
                False,        # Enable Upload again
                "Choose json or parquet file",
                {}
            )
        
        # Callback to enable Drawing to the user:
        @app.callback(
            Output("eva-overscale-draw-meta", "data", allow_duplicate=True),
            Output("edit-control", "drawToolbar", allow_duplicate= True),
            Input("eva-overscale-sa-draw", "n_clicks"),
            prevent_initial_call=True
        )
        def draw_eva_overscale_sa(sa):
            if not (sa):
                raise PreventUpdate
            ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
            layer_key, color = COLOR[ctx]
            return {"layer": layer_key, "color": color}, {"mode": "polygon", "n_clicks": int(time.time())}
        
        # Callback to add the polygon to the map
        @app.callback(
            Output("eva-overscale-draw", "children"),
            Output("draw-len", "data", allow_duplicate=True),
            Output("edit-control", "editToolbar", allow_duplicate=True),
            Input("edit-control", "geojson"),
            State("draw-len", "data"),
            State("eva-overscale-draw-meta", "data"),
            State("eva-overscale-draw", "children"),
            prevent_initial_call=True
        )
        def add_sa_polygon(gj, prev_len, meta, ch_sa):
            ctx = dash.callback_context
            trig = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

            # Normaliza children actuales
            ch_sa    = list(ch_sa or [])

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
                return ch_sa, 0, clear

            color = (meta or {}).get("color", "#ff00ff")
            layer = (meta or {}).get("layer", "wind")
            comps = [dl.Polygon(positions=p, color=color, fillColor=color, fillOpacity=0.6, weight=4)
                    for p in new_polys]

            if layer == "study-area":
                ch_sa.extend(comps)

            # Limpia el EditControl y resetea contador para evitar "azules intermedios"
            clear = {"mode": "remove", "action": "clear all", "n_clicks": int(time.time())}
            return ch_sa, 0, clear
        
        # Callback to check if the file is valid. If extension is not valid we add a error message, if it is valid we store it and save it as a GeoJSON:
        @app.callback(
            Output("eva-overscale-sa-file-label", "children", allow_duplicate=True),
            Output("eva-overscale-sa-file", "className", allow_duplicate=True),
            Output("eva-overscale-file-store", "data", allow_duplicate=True),
            Input("eva-overscale-sa-file", "filename"),
            Input("eva-overscale-sa-file", "contents"),
            State("eva-overscale-file-store", "data"),
            State("session-id", "data"),
            prevent_initial_call=True
        )
        def on_upload_sa(filename, contents, prev_store, sid):
            if not filename:
                raise PreventUpdate
            label_text = filename
            if not _valid_ext(filename):
                return label_text, INVALID_UPLOAD_CLASS, {"valid": False, "reason": "bad_extension"}
            if not contents:
                return label_text, BASE_UPLOAD_CLASS, no_update
            try:
                sid = sid if isinstance(sid, str) and sid else None
                out_path = _save_upload_to_disk(contents, filename, "eva_overscale_study_area", sid)
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
                    "kind": "eva_overscale_study_area",
                    "filename": filename,
                    "ext": os.path.splitext(filename)[1].lower(),
                    "path": out_path,
                    "ts": int(time.time()),
                    "sid": sid
                }
                return label_text, BASE_UPLOAD_CLASS, payload
            except Exception as e:
                return f"{filename} — error: {e}", INVALID_UPLOAD_CLASS, {"valid": False, "error": str(e)}
            
        # Callback to syinchronize UI:
        @app.callback(
            Output("eva-overscale-sa-draw", "disabled", allow_duplicate=True),
            Output("eva-overscale-sa-file", "disabled", allow_duplicate=True),
            Output("eva-overscale-draw", "children", allow_duplicate=True),
            Output("eva-overscale-file-store", "data", allow_duplicate=True),
            Output("eva-overscale-upload", "children", allow_duplicate=True),
            Output("eva-overscale-sa-file-label", "children", allow_duplicate=True),
            Output("eva-overscale-sa-file", "filename", allow_duplicate=True),
            Output("eva-overscale-sa-file", "contents", allow_duplicate=True),
            Output("eva-overscale-sa-file", "className"),
            Input("eva-overscale-file-store", "data"),
            Input("eva-overscale-draw", "children"),
            Input("eva-overscale-reset-button", "n_clicks"),
            State("session-id", "data"),
            prevent_initial_call=True
        )
        def sync_eva_overscale_ui(store, drawn_children, n_reset, sid):
            trig_id = (ctx.triggered_id if hasattr(ctx, "triggered_id") else None)

            # Reset: clear UI and memory:
            if trig_id == "eva-overscale-reset-button":
                try:
                    _rm_tree(_session_dir("eva_overscale_study_area", sid))
                except Exception:
                    pass
                return (
                    False,                      # draw habilitado
                    False,                      # upload habilitado
                    [],                         # sin polígonos dibujados
                    None,                       # limpiar store
                    [],                         # limpiar capa subida
                    "Choose json or parquet file",  # label por defecto
                    None, None,                 # filename/contents -> None (permite re-subir el mismo)
                    UPLOAD_CLASS,               # clase neutra
                )

            file_present = isinstance(store, dict) and store.get("valid") is True
            has_drawn = (isinstance(drawn_children, list) and len(drawn_children) > 0) or bool(drawn_children)

            if file_present:
                return True, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            return False, has_drawn, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Callback to paint the uploaded file:
        @app.callback(                                                                                  
            Output("eva-overscale-upload", "children"),                                                     # salida: capa pintada en el mapa
            Input("eva-overscale-file-store", "data"),                                                           # entrada: cambios en el Store de wind
            prevent_initial_call=True                                                                   
        )
        def paint_eva_sa_uploaded(data):                                                                  
            if not data or not isinstance(data, dict):                                                  
                raise PreventUpdate                                                                      # no actualizar si no hay nada
            if not data.get("valid"):                                                                   
                return []                                                                                # limpiar capa si hubo intento inválido

            path = data.get("path")
            print(f"[EVA] path -> {data.get('path')}", file=sys.stderr, flush=True)
            print(f"[EVA] exists? {os.path.exists(data.get('path'))}", file=sys.stderr, flush=True)                                                                      # ruta del archivo guardado en la carpeta de la sesion
            ext  = (data.get("ext") or "").lower()                                                      

            # estilo común para polígonos/líneas (Leaflet aplicará estilo a features no puntuales)       
            style = dict(color="#015B97", weight=3, fillColor="#015B97", fillOpacity=0.4)               # estilo Wind

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
                    id=f"eva-overscale-upload-{data.get('ts', 0)}"                                                # id único por timestamp
                )
                return [layer]                                                                           # devolver lista con la capa
            except Exception:                                                                             
                return []
