# from zipfile import ZipFile
from typing import Dict, Tuple, List

import dash, json, time, os, sys, shutil, re 
from dash import Input, Output, State, no_update, html, dcc, ALL, ctx, MATCH
from dash.exceptions import PreventUpdate
# from dash_extensions.javascript import assign
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import dash_leaflet as dl
import dash_bootstrap_components as dbc
from shapely.geometry import shape, Polygon


from app.callbacks.management_callbacks import _valid_ext, _save_upload_to_disk, _to_geojson_from_parquet, _detect_lonlat_columns, _df_to_feature_collection_from_polygon, _estimate_b64_size, _rm_tree, _session_dir
from app.models.eva_mpaeu import run_selected_assessments, EVA_MPAEU
from app.models.eva_obis import create_quadrat_grid

# Classes:
COLOR = {"eva-overscale-sa-draw": ("study-area",   "#015B97")}
UPLOAD_CLASS = "form-control form-control-lg"
BASE_UPLOAD_CLASS = "form-control is-valid form-control-lg"               
INVALID_UPLOAD_CLASS = "form-control is-invalid form-control-lg"  

# List of AQ used for EVA Overscale:
AQ_LIST = (1, 5, 7, 10, 12, 14)

COLORS = ['#edf8e9','#bae4b3','#74c476','#31a354','#006d2c']

# Function to get the release version:
def app_version() -> str:
    try:
        import subprocess

        # 1) ¿Hay un tag exactamente en HEAD?
        exact = subprocess.check_output(
            ["git", "tag", "--points-at", "HEAD"],
            text=True
        ).strip()
        if exact:
            # si hay varios, coge el primero
            return exact.splitlines()[0]

        # 2) Si no hay tag exacto, toma el más reciente alcanzable
        return subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            text=True
        ).strip()
    except Exception:
        return "unknown"

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


# Utils to run EVA Overscale:
def _positions_to_shapely(positions):
    if not positions:
        return None

    ring = positions
    if isinstance(ring[0], (list, tuple)) and len(ring) > 0 and isinstance(ring[0][0], (list, tuple)):
        ring = ring[0]  

    # Convert to [lon, lat]
    coords = [(lon, lat) for lat, lon in ring if lat is not None and lon is not None]
    if len(coords) < 3:
        return None

    # Close polygons in case are not correctly closed (should be):
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    try:
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None
    except Exception:
        return None

def _iter_children(children):
    """Normalize children to plain list."""
    if children is None:
        return []
    return children if isinstance(children, (list, tuple)) else [children]

def _get_prop_eva(component, prop):
    """ Get component properties from Dash dictionary"""
    try:
        # If they are serialized:
        return component.get("props", {}).get(prop)
    except Exception:
        # if they are BaseComponent:
        return getattr(component, prop, None)

def aoi_from_featuregroups(sa_draw_children, sa_upload_children) -> gpd.GeoDataFrame:
    """
    Get geometries of draw and upload study area and return a GeoDataframe in EPSG:4326 (same CRS of MPAEU results)
    """
    all_feats = []

    for ch in _iter_children(sa_draw_children) + _iter_children(sa_upload_children):
        # 1) GeoJSON
        data = _get_prop_eva(ch, "data")
        if data:
            feats = []
            if data.get("type") == "FeatureCollection":
                feats = data.get("features", [])
            elif data.get("type") == "Feature":
                feats = [data]

            for f in feats:
                geom = (f or {}).get("geometry")
                if not geom:
                    continue
                try:
                    g = shape(geom)
                    if g.is_empty:
                        continue
                    all_feats.append({"geometry": g, **(f.get("properties") or {})})
                except Exception:
                    pass
            continue  

        # 2) Polygon (Leaflet)
        ctype = getattr(ch, "type", None) or (ch.get("type") if isinstance(ch, dict) else None)
        if ctype == "Polygon":
            positions = _get_prop_eva(ch, "positions")
            poly = _positions_to_shapely(positions)
            if poly is not None:
                all_feats.append({"geometry": poly})
            continue

    if not all_feats:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(all_feats, geometry="geometry", crs="EPSG:4326")
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()
    if gdf.empty:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    return gdf

# Wrapper H3 that acepts GDF directly
def create_h3_grid_from_gdf(aoi_gdf: gpd.GeoDataFrame, h3_resolution: int) -> gpd.GeoDataFrame:
    import h3  
    resolution = int(h3_resolution)
    if not (0 <= resolution <= 15):
        raise ValueError("resolution debe estar entre 0 y 15 (entero).")

    aoi = aoi_gdf.to_crs(4326) if aoi_gdf.crs else aoi_gdf.set_crs(4326)
    geoms = aoi.geometry.explode(index_parts=False)
    if geoms.empty:
        return gpd.GeoDataFrame(columns=["h3", "geometry"], crs="EPSG:4326")

    union_geom = geoms.unary_union
    if union_geom.is_empty:
        return gpd.GeoDataFrame(columns=["h3", "geometry"], crs="EPSG:4326")

    # Individual polygons
    polygons = []
    for geom in geoms:
        if geom.is_empty:
            continue
        if geom.geom_type == "Polygon":
            polygons.append(geom)
        elif geom.geom_type == "MultiPolygon":
            polygons.extend(list(geom.geoms))

    cells = set()
    for poly in polygons:
        # Delete Z in case it exists
        if hasattr(poly, "has_z") and poly.has_z:
            poly = Polygon(
                [(x, y) for x, y, *_ in np.asarray(poly.exterior.coords)],
                holes=[[(x, y) for x, y, *_ in np.asarray(r.coords)] for r in poly.interiors]
            )
        cells.update(h3.geo_to_cells(poly, res=resolution))

    if not cells:
        return gpd.GeoDataFrame(columns=["h3", "geometry"], crs="EPSG:4326")

    all_cells = {nb for c in cells for nb in h3.grid_disk(c, k=5)}
    hex_geoms = [(cid, Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cid)])) for cid in all_cells]
    hex_df = gpd.GeoDataFrame(hex_geoms, columns=["h3", "geometry"], crs="EPSG:4326")
    return hex_df[hex_df.intersects(union_geom)].reset_index(drop=True)

# ------------------------------------------------------------------------

# Function to compose the Accordion with the Functional Groups passes by the user:
def _build_legend_eva_overscale() -> html.Div:
    colors = ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"]
    labels = ["Very low (0–1)", "Low (1–2)", "Medium (2–3)", "High (3–4)", "Very high (4–5)"]

    box_style_base = {
        "width": "20px",
        "height": "12px",
        "display": "inline-block",
        "marginRight": "6px",
        "border": "1px solid #333",
        "borderRadius": "2px"
    }

    # NoData Style:
    no_data_box_style = {
        **box_style_base,
        "backgroundColor": "transparent",
        "backgroundImage": (
            "repeating-linear-gradient("
            "45deg, rgba(0,0,0,0.9) 0 2px, rgba(0,0,0,0) 2px 4px)"
        )
    }

    return html.Div(
        className="legend",
        children=[
            html.Div("Condition", style={"fontWeight": "bold", "marginBottom": "6px"}),
            html.Div( 
                className="legend-item",
                children=[
                    html.Div(style=no_data_box_style),
                    html.Span("No Data"),
                ],
                style={"marginBottom": "4px"}
            ),
            *[
                html.Div(
                    className="legend-item",
                    children=[
                        html.Div(style={**box_style_base, "backgroundColor": color}),
                        html.Span(label)
                    ],
                    style={"marginBottom": "4px"}
                )
                for color, label in zip(colors, labels)
            ],
        ],
    )

def _results_dir_from_store(store_data: dict) -> Path | None:
    """
    Points results directori from store
    """
    try:
        zip_path = Path(store_data.get("zip_path"))
        if not zip_path.exists():
            return None
        base = zip_path.stem
        stamp = base.replace("eva_overscale_", "", 1)
        results_dir = zip_path.parent / f"results_eva_overscale_{stamp}"
        return results_dir if results_dir.exists() else None
    except Exception:
        return None
    
def _slugify_name_for_match(name: str) -> str:
    """normaliza nombres a clave comparable (minúsculas, guiones)."""
    s = name.strip().lower().replace("_", " ")
    s = re.sub(r"\s+", "-", s)
    return re.sub(r"[^a-z0-9-]", "", s)

def _parquet_for_group(results_dir: Path, group_key: str) -> Path | None:
    """
    Busca el parquet cuyo nombre (sin extensión) coincide con el grupo,
    admitiendo diferencias de '_' vs '-' y espacios.
    """
    if not results_dir or not results_dir.exists():
        return None
    gkey = _slugify_name_for_match(group_key)
    for p in results_dir.glob("*.parquet"):
        key = _slugify_name_for_match(p.stem)   # ej.: "Angiosperms" -> "angiosperms"
        if key == gkey:
            return p
    return None

def _parquet_to_binned_featurecollections(parquet_path: Path, aq_col: str):
    gdf = gpd.read_parquet(parquet_path).copy()

    # CRS → WGS84
    if gdf.crs is None:
        gdf.set_crs(4326, inplace=True)
    elif getattr(gdf.crs, "to_epsg", lambda: None)() not in (None, 4326):
        gdf = gdf.to_crs(4326)

    # locate columns
    cols_lc = {c.lower(): c for c in gdf.columns}
    target = aq_col.lower()
    real_col = cols_lc.get(target)
    if real_col is None:
        tnorm = target.replace("_", "")
        for lc, orig in cols_lc.items():
            if lc.replace("_", "") == tnorm:
                real_col = orig
                break

    if real_col is None:
        return {i: {"type": "FeatureCollection", "features": []} for i in (-1, 0, 1, 2, 3, 4)}

    vals = pd.to_numeric(gdf[real_col], errors="coerce")

    nodata_mask = vals.isna() | (vals < 0)

    vals_clip = vals.clip(lower=0.0, upper=5.0)
    bin_ids = pd.cut(
        vals_clip, bins=[0, 1, 2, 3, 4, 5],
        labels=[0, 1, 2, 3, 4],
        include_lowest=True
    ).astype("Int64") 

    gdf["_bin"] = np.where(nodata_mask, -1, bin_ids.fillna(0).astype(int))

    out = {}
    for i in (-1, 0, 1, 2, 3, 4):
        sub = gdf[gdf["_bin"] == i]
        if sub.empty:
            out[i] = {"type": "FeatureCollection", "features": []}
        else:
            out[i] = json.loads(sub.to_json())
    return out

def load_geojson_bins_for(group_key: str, aq_value: str, store_data: dict) -> dict:
    if not store_data or "zip_path" not in store_data:
        return {}
    results_dir = _results_dir_from_store(store_data)
    if not results_dir:
        return {}
    parquet_path = _parquet_for_group(results_dir, group_key)
    if not parquet_path:
        return {}
    return _parquet_to_binned_featurecollections(parquet_path, aq_value)

def _slugify(txt: str) -> str:
    """Id seguro para pattern-matching: minúsculas y solo [a-z0-9_-]."""
    txt = txt.strip().lower()
    txt = re.sub(r"\s+", "-", txt)
    return re.sub(r"[^a-z0-9_-]", "", txt) or "group"

def build_results_ui(fg_configs: Dict) -> Tuple[html.Div, List[dl.LayerGroup]]:
    """
    Constructs the Accordion and AccordionItens from the functional groups and AQs.
    """
    accordion_items = []
    layer_groups: List[dl.LayerGroup] = []

    # Filtramos keys that represent groups
    for k, cfg in (fg_configs or {}).items():
        if not isinstance(cfg, dict):
            continue
        name = cfg.get("name") or f"Group {k}"
        group_key = _slugify(name) or f"g{k}"

        # Switch + Radios 
        header_row = dbc.Row(
            [
                dbc.Col(dbc.Badge(name, color="light", text_color="dark"), width="auto"),
                dbc.Col(
                    dbc.Switch(
                        id={"type": "fg-visible", "group": group_key},
                        # label=f"{group_key}",
                        value=False,               # por defecto apagado
                    ),
                    width="auto",
                    className="ms-auto"
                ),
            ],
            className="align-items-center g-2 mb-2"
        )

        radios = dbc.RadioItems(
            id={"type": "fg-aq-radio", "group": group_key},
            options=[{"label": f"AQ{n}", "value": f"aq{n}"} for n in AQ_LIST],
            value="aq1",                          # por defecto
            inputClassName="me-2 d-inline",
            labelClassName="form-check-label",
            className="ms-2"
        )

        accordion_items.append(
            dbc.AccordionItem(
                [header_row, radios],
                title= html.Span(name, className="form-check-label"),
                item_id=group_key
            )
        )

        # Capa contenedora de resultados por grupo
        layer_groups.append(
            dl.LayerGroup(id={"type": "fg-layer", "group": group_key})
        )

    accordion = dbc.Accordion(
        accordion_items or [dbc.AccordionItem("No groups found", title="Results")],
        always_open=True,
        start_collapsed=False,
        className="p-2"
    )

    return accordion, layer_groups



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
            Output("eva-overscale-results", "disabled", allow_duplicate=True),
            Output("eva-results-accordion-container", "children", allow_duplicate=True),
            Output("eva-overscale-legend-div", "children"),
            Output("eva-aq-layer", "children", allow_duplicate=True),
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
                {},
                True,         # EVA Overscale results download button
                [],           # Clear Accordion
                [],           # Clear Legend
                []            # Clear GeoJsons of results added to the dl.Map
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
            

        # Callback to Run the EVA Overscale with MPAEU results:
        @app.callback(
            Output("eva-overscale-results", "disabled"),
            Output("eva-results-store", "data"),
            Output("eva-results-accordion-container", "children", allow_duplicate=True),
            Output("eva-aq-layer", "children"),
            Output("eva-overscale-legend-div", "children", allow_duplicate=True),
            Output("eva-overscale-draw", "children", allow_duplicate=True),
            Output("eva-overscale-upload", "children", allow_duplicate=True),
            Input("eva-overscale-run-button", "n_clicks"),
            State("fg-configs", "data"),
            State("ag-size-store", "data"),
            State("eva-overscale-draw", "children"),
            State("eva-overscale-upload", "children"),
            State("session-id", "data"),
            prevent_initial_call=True,
        )
        def run_eva_overscale(n_clicks, fg_params, ag_store, sa_draw_children, sa_upload_children, session_id):
            if not n_clicks:
                raise PreventUpdate

            aoi_gdf = aoi_from_featuregroups(sa_draw_children, sa_upload_children)
            if aoi_gdf.empty:
                return no_update, no_update

            ag_store = ag_store or {}
            grid_type = ag_store.get("type")
            grid_size = ag_store.get("size")
            if grid_type == "quadrat":
                grid_gdf = create_quadrat_grid(aoi_gdf, grid_size=int(grid_size))
            elif grid_type == "h3":
                grid_gdf = create_h3_grid_from_gdf(aoi_gdf, h3_resolution=int(grid_size))
            else:
                return no_update, no_update

            eva = EVA_MPAEU(model="mpaeu", method="ensemble", scenario="current_cog")
            eva_results_by_fg = {}

            cfgs = fg_params or {}
            group_keys = [k for k in cfgs if k.isdigit()]
            if not group_keys:
                return no_update, no_update

            for gkey in sorted(group_keys, key=int):
                cfg = cfgs[gkey]
                lrf = cfg.get("lrf", {})
                nrf = cfg.get("nrf", {})

                parameters = {
                    "aq1":  {"taxon_ids": lrf.get("taxon_ids", []), "cut_lrf": lrf.get("threshold_pct")},
                    "aq5":  {"taxon_ids": nrf.get("taxon_ids", []), "country_name": cfg.get("eez_country"),
                            "grid_size": cfg.get("eez_grid_size"), "cut_nrf": nrf.get("threshold_pct")},
                    "aq7":  {"taxon_ids": sorted(set(lrf.get("taxon_ids", []) + nrf.get("taxon_ids", []) +
                                                    cfg.get("esf_taxon_ids", []) + cfg.get("hfsbh_taxon_ids", []) + cfg.get("mss_taxon_ids", [])))},
                    "aq10": {"taxon_ids": cfg.get("esf_taxon_ids", [])},
                    "aq12": {"taxon_ids": cfg.get("hfsbh_taxon_ids", [])},
                    "aq14": {"taxon_ids": cfg.get("mss_taxon_ids", [])},
                }

                try:
                    result, aq_meta = run_selected_assessments(eva=eva, grid=grid_gdf, params=parameters)
                    eva_results_by_fg[gkey] = (cfg.get("name", f"group_{gkey}"), result, aq_meta)
                except Exception as e:
                    print(f"[EVA] ERROR in FG {gkey}: {e}", file=sys.stderr)

            if not eva_results_by_fg:
                return no_update, no_update

            # Save in directory session:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            base_dir = _session_dir("eva_overscale_study_area", session_id)
            results_dir = Path(base_dir) / f"results_eva_overscale_{stamp}"
            results_dir.mkdir(parents=True, exist_ok=True)

            # Configuration with metadata:
            fg_with_meta = {}
            for gkey, cfg in (fg_params or {}).items():
                name, result, aq_meta = eva_results_by_fg.get(gkey, (cfg.get("name", f"group_{gkey}"), None, {}))
                # guarda parquet como ya haces
                if result is not None:
                    filename = name.replace(" ", "_") + ".parquet"
                    result.to_parquet(results_dir / filename)

                # mezcla config del usuario + metadatos de AQs
                fg_with_meta[gkey] = {
                    **cfg,
                    "aqs": aq_meta,  
                }

            # Save configuration
            config_path = results_dir / "configuration.json"
            config_payload = {
                "version": app_version(),
                "assessment_day": time.strftime("%Y_%m_%d"),
                "aoi": {"crs": "EPSG:4326", "bbox": list(aoi_gdf.total_bounds) if not aoi_gdf.empty else None},
                "assessment_grid": {"type": grid_type, "size": int(grid_size) if grid_size is not None else None},
                "functional_groups": fg_with_meta,   
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_payload, f, ensure_ascii=False, indent=2)

            # Create ZIP
            zip_path = Path(base_dir) / f"eva_overscale_{stamp}.zip"
            shutil.make_archive(zip_path.with_suffix("").as_posix(), "zip", root_dir=results_dir)

            # Create Accordion and LayerGroup to add to map:
            accordion, layer_groups = build_results_ui(fg_params or {})

            # Build legend:
            legend = _build_legend_eva_overscale()


            # Enable download button and return ZIP path
            return False, {"zip_path": str(zip_path)}, accordion, layer_groups, legend, [], []

        # Callback to download EVA overscale results:
        @app.callback(
            Output("eva-overscale-download", "data"),
            Input("eva-overscale-results", "n_clicks"),
            State("eva-results-store", "data"),
            prevent_initial_call=True,
        )
        def download_eva_results(n_clicks, store_data):
            if not store_data or "zip_path" not in store_data:
                raise PreventUpdate

            zip_path = Path(store_data["zip_path"])
            if not zip_path.exists():
                print(f"[EVA] ZIP not found: {zip_path}", file=sys.stderr)
                raise PreventUpdate

            return dcc.send_file(str(zip_path))
        
        # Callback that displays groups and the selected AQ:
        @app.callback(
            Output({"type":"fg-layer","group":MATCH}, "children"),
            Input({"type":"fg-visible","group":MATCH}, "value"),
            Input({"type":"fg-aq-radio","group":MATCH}, "value"),
            State("eva-results-store","data"),
            State({"type":"fg-layer","group":MATCH}, "id"),
            prevent_initial_call=True
        )
        def toggle_group_layer(show, aq_value, store_data, layer_id):
            if not show:
                return []
            if not aq_value:
                raise PreventUpdate

            group_key = layer_id["group"]
            bins_fc = load_geojson_bins_for(group_key, aq_value, store_data)
            if not bins_fc:
                return []

            layers = []
            did_zoom = False
            for i in (-1, 0, 1, 2, 3, 4):
                fc = bins_fc.get(i, {"type":"FeatureCollection","features":[]})
                if not fc.get("features"):
                    continue

                if i == -1:
                    # NoData: borde negro, trazo discontinuo, sin relleno
                    style = dict(weight=2, color="#000000", dashArray="4 3", fill=False, fillOpacity=0.0)
                else:
                    color = COLORS[i]
                    style = dict(weight=2, color=color, fillColor=color, fillOpacity=0.7)

                layers.append(
                    dl.GeoJSON(
                        id={"type":"fg-geojson","group":group_key,"aq":aq_value,"bin":i},
                        data=fc,
                        options=dict(style=style),
                        zoomToBounds=(not did_zoom)
                    )
                )
                did_zoom = True

            return layers
        
        @app.callback(
            Output("fg-configs", "data", allow_duplicate=True),
            Output("eva-overscale-draw", "children", allow_duplicate=True),
            Output("eva-overscale-upload", "children", allow_duplicate=True),
            Output("eva-overscale-file-store", "data", allow_duplicate=True),
            Output("eva-results-accordion-container", "children", allow_duplicate=True),
            Output("eva-overscale-legend-div", "children", allow_duplicate=True),
            Output("eva-aq-layer", "children", allow_duplicate=True),
            Input("tabs", "value"),
            prevent_initial_call=True
        )
        def clear_overlay_on_tab_change(tab_value):
            if tab_value != "tab-eva-overscale":
                return {},[],[],{},[],[],[]            # limpiar overlay al salir del tab
            raise PreventUpdate
