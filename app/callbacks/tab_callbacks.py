from dash import Input, Output, html, dcc
from dash.dependencies import State
from dash import callback
import dash

def register_tab_callbacks(app: dash.Dash):
    @app.callback(
        Output("tab-content", "children"),
        Input("tabs", "value")
    )
    def render_tab(tab):
        if tab == "tab-saltmarsh":
            return html.Div([
                # Tres dropdowns en vertical
                dcc.Dropdown(
                    id="study-area-dropdown",
                    options=[
                        {"label": "Area 1", "value": "area1"},
                        {"label": "Area 2", "value": "area2"},
                        {"label": "Area 3", "value": "area3"},
                    ],
                    placeholder="Select Study Area",
                    style={"marginBottom": "10px", "width": "100%"}
                ),
                dcc.Dropdown(
                    id="scenario-dropdown",
                    options=[
                        {"label": "Scenario A", "value": "A"},
                        {"label": "Scenario B", "value": "B"},
                        {"label": "Scenario C", "value": "C"},
                    ],
                    placeholder="Select Climate Change Scenario",
                    style={"marginBottom": "10px", "width": "100%"}
                ),
                dcc.Dropdown(
                    id="year-dropdown",
                    options=[
                        {"label": "2025", "value": 2025},
                        {"label": "2030", "value": 2030},
                        {"label": "2040", "value": 2040},
                    ],
                    placeholder="Prediction Year",
                    style={"marginBottom": "20px", "width": "100%"}
                ),
                # Aquí iría después tu gráfica, etc.
                html.Div(id="saltmarsh-chart")
            ])
        else:
            # Para otras pestañas, pones tu contenido actual
            return html.Div(f"Contenido de {tab}")

# Luego, en el create_app():
# from .callbacks.tab_callbacks import register_tab_callbacks
# register_tab_callbacks(app)
