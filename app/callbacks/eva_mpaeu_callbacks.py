import dash, json
from dash import Input, Output, State, no_update, html, dcc, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

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
            Output("fg-selected-index", "data"),
            Output("fg-last-click-ts", "data"),  # actualizar el último timestamp usado
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
            Output("fg-configs", "data"),
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
        
        # Callback to test that the functional group configuration has been saved correctly:
        # @app.callback(
        #     Output("download-fg-configs", "data"),
        #     Input("btn-download-fg", "n_clicks"),
        #     State("fg-configs", "data"),
        #     prevent_initial_call=True
        # )
        # def download_configs(n, data):
        #     if not n or not data:
        #         raise PreventUpdate
        #     payload = json.dumps(data, indent=2, ensure_ascii=False)
        #     return dcc.send_string(payload, "functional_groups_config.json")

