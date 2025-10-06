import dash, json
from dash import Input, Output, State, no_update, html, dcc, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# # Functions to create a ´matrix´ to include Funtional Group configuration:
# def funct_group_config_matrix(i: int):
#     """
#     Devuelve las 6 filas (dbc.Row) con 3 columnas (dbc.Col) cada una.
#     Solo se rellenan las posiciones:
#     (0,0), (1,0), (1,1), (2,0), (2,1), (2,2), (3,0), (4,0), (5,0).
#     """
#     # Widgets por coordenada (fila, col)
#     cells = {
#         (0, 0): html.Div([
#             html.Small("Group Name:"),
#             dcc.Input(
#                 id=f"fg-{i}-name",
#                 type="text",
#                 placeholder="Add Functional Group",
#                 className="form-control",
#             ),
#         ]),

#         (1, 0): html.Div([
#             html.Small("Functional Type"),
#             dcc.Dropdown(
#                 id=f"fg-{i}-type",
#                 options=[{"label": x, "value": x} for x in ["Producer", "Consumer", "Decomposer"]],
#                 placeholder="Select…",
#                 clearable=True,
#             ),
#         ]),

#         (1, 1): html.Div([
#             html.Small("Weight"),
#             dcc.Input(
#                 id=f"fg-{i}-weight",
#                 type="number",
#                 min=0, step=0.1, value=1.0,
#                 className="form-control",
#             ),
#         ]),

#         (2, 0): html.Div([
#             html.Small("Features"),
#             dcc.Checklist(
#                 id=f"fg-{i}-features",
#                 options=[{"label": "ESF", "value": "esf"},
#                          {"label": "HFS/BH", "value": "hfs"},
#                          {"label": "MSS", "value": "mss"}],
#                 value=[],
#                 inputClassName="form-check-input",
#                 labelClassName="form-check-label",
#                 className="d-flex gap-3"
#             ),
#         ]),

#         (2, 1): html.Div([
#             html.Small("Threshold"),
#             dcc.Input(
#                 id=f"fg-{i}-threshold",
#                 type="number",
#                 min=0, step=1, value=10,
#                 className="form-control",
#             ),
#         ]),

#         (2, 2): html.Div([
#             html.Small("Active"),
#             dbc.Checkbox(
#                 id=f"fg-{i}-active",
#                 value=True,
#                 className="ms-2",
#                 switch=True,
#             ),
#         ]),

#         (3, 0): html.Div([
#             html.Small("Notes"),
#             dcc.Textarea(
#                 id=f"fg-{i}-notes",
#                 className="form-control",
#                 placeholder="Optional notes…",
#                 style={"height": "80px"}
#             ),
#         ]),

#         (4, 0): html.Div([
#             html.Small("Upload (optional)"),
#             dcc.Upload(
#                 id=f"fg-{i}-upload",
#                 children=html.Div(["Drag & Drop or ", html.A("Select File")]),
#                 className="border rounded-3 p-3 text-center",
#             ),
#         ]),

#         (5, 0): html.Div([
#             dbc.Button(
#                 "Remove Group",
#                 id=f"fg-{i}-remove",
#                 color="outline-danger",
#                 className="w-100"
#             )
#         ]),
#     }

    # rows = []
    # for r in range(6):
    #     row_cols = []
    #     for c in range(3):
    #         content = cells.get((r, c), html.Div())  # vacío si no hay widget en esa celda
    #         row_cols.append(
    #             dbc.Col(content, width=4)  # 12/3 = 4 → 3 columnas iguales
    #         )
    #     rows.append(dbc.Row(row_cols, className="g-2"))  # g-2 = gutter
    # return rows


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
                    id=btn_id,                      # ← ID patrón
                    n_clicks=0,
                    className="btn btn-outline-primary w-100"
                )
            )

            # dbc.Tooltip puede usar el mismo ID patrón como target (dbc>=1.5)
            tooltip_children.append(
                dbc.Tooltip(
                    f"Group {i} configuration",
                    target=btn_id,                  # ← apuntar al mismo ID patrón
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
                # Dash antiguo
                prop_id = (ctx.triggered[0]["prop_id"] if ctx.triggered else "")
                if prop_id.startswith("add-functional-group."):
                    raise PreventUpdate

            if not ts_list or all((t or 0) == 0 for t in ts_list):
                raise PreventUpdate

            # Buscar el botón realmente clicado más recientemente
            # (máximo timestamp > last_ts)
            ts_list = [(t or 0) for t in ts_list]
            max_ts = max(ts_list)
            if max_ts <= (last_ts or 0):
                # No hay click “nuevo” desde la última vez (probablemente un re-render)
                raise PreventUpdate

            # Índice en la lista (0-based) del botón con timestamp máximo
            idx0 = ts_list.index(max_ts)
            # Como usas ids {"type":"fg-button", "index": i} donde i empieza en 1,
            # el índice i será idx0 + 1
            i = idx0 + 1

            return True, f"Configure Group {i}", i, max_ts
        
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
            # aquí podrías leer los inputs y guardar en un Store por grupo
            return False

