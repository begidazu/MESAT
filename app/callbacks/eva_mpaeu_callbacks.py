import dash
from dash import Input, Output, State, no_update, html, dcc
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# Functions to create a ´matrix´ to include Funtional Group configuration:
def funct_group_config_matrix(i: int):
    """
    Devuelve las 6 filas (dbc.Row) con 3 columnas (dbc.Col) cada una.
    Solo se rellenan las posiciones:
    (0,0), (1,0), (1,1), (2,0), (2,1), (2,2), (3,0), (4,0), (5,0).
    """
    # Widgets por coordenada (fila, col)
    cells = {
        (0, 0): html.Div([
            html.Small("Group Name:"),
            dcc.Input(
                id=f"fg-{i}-name",
                type="text",
                placeholder="Add Functional Group",
                className="form-control",
            ),
        ]),

        (1, 0): html.Div([
            html.Small("Functional Type"),
            dcc.Dropdown(
                id=f"fg-{i}-type",
                options=[{"label": x, "value": x} for x in ["Producer", "Consumer", "Decomposer"]],
                placeholder="Select…",
                clearable=True,
            ),
        ]),

        (1, 1): html.Div([
            html.Small("Weight"),
            dcc.Input(
                id=f"fg-{i}-weight",
                type="number",
                min=0, step=0.1, value=1.0,
                className="form-control",
            ),
        ]),

        (2, 0): html.Div([
            html.Small("Features"),
            dcc.Checklist(
                id=f"fg-{i}-features",
                options=[{"label": "ESF", "value": "esf"},
                         {"label": "HFS/BH", "value": "hfs"},
                         {"label": "MSS", "value": "mss"}],
                value=[],
                inputClassName="form-check-input",
                labelClassName="form-check-label",
                className="d-flex gap-3"
            ),
        ]),

        (2, 1): html.Div([
            html.Small("Threshold"),
            dcc.Input(
                id=f"fg-{i}-threshold",
                type="number",
                min=0, step=1, value=10,
                className="form-control",
            ),
        ]),

        (2, 2): html.Div([
            html.Small("Active"),
            dbc.Checkbox(
                id=f"fg-{i}-active",
                value=True,
                className="ms-2",
                switch=True,
            ),
        ]),

        (3, 0): html.Div([
            html.Small("Notes"),
            dcc.Textarea(
                id=f"fg-{i}-notes",
                className="form-control",
                placeholder="Optional notes…",
                style={"height": "80px"}
            ),
        ]),

        (4, 0): html.Div([
            html.Small("Upload (optional)"),
            dcc.Upload(
                id=f"fg-{i}-upload",
                children=html.Div(["Drag & Drop or ", html.A("Select File")]),
                className="border rounded-3 p-3 text-center",
            ),
        ]),

        (5, 0): html.Div([
            dbc.Button(
                "Remove Group",
                id=f"fg-{i}-remove",
                color="outline-danger",
                className="w-100"
            )
        ]),
    }

    rows = []
    for r in range(6):
        row_cols = []
        for c in range(3):
            content = cells.get((r, c), html.Div())  # vacío si no hay widget en esa celda
            row_cols.append(
                dbc.Col(content, width=4)  # 12/3 = 4 → 3 columnas iguales
            )
        rows.append(dbc.Row(row_cols, className="g-2"))  # g-2 = gutter
    return rows


def register_eva_mpaeu_callbacks(app: dash.Dash):

    @app.callback(
        Output("fg-list-container", "children"),
        Input("add-functional-group", "n_clicks"),
        State("fg-list-container", "children"),
        prevent_initial_call=True
    )
    def add_functional_group(n_clicks, children):
        if not n_clicks:
            raise PreventUpdate
        children = children or []
        i = len(children) + 1  
        children.append(
            html.Div(
                id=f"fg-list-div-{i}",
                className="mb-3",
                children=[
                    html.Div(className="fw-bold mb-2", children=f"Group {i}")
                ]
            )
        )
        return children