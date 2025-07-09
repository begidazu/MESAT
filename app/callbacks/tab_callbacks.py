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
                        {"label": "Urdaibai Estuary", "value": "area1"},
                        {"label": "Bay of Santander", "value": "area2"},
                        {"label": "Cadiz Bay", "value": "area3"},
                    ],
                    placeholder="Select Study Area",
                    style={"marginBottom": "10px", "width": "80%"}
                ),
                dcc.Dropdown(
                    id="scenario-dropdown",
                    options=[
                        {"label": "Regional RCP4.5", "value": "A"},
                        {"label": "Regional RCP8.5", "value": "B"},
                        {"label": "Global RCP4.5", "value": "C"},
                    ],
                    placeholder="Select Climate Change Scenario",
                    style={"marginBottom": "10px", "width": "80%"}
                ),
                dcc.Dropdown(
                    id="year-dropdown",
                    options=[
                        {"label": "2025", "value": 2025},
                        {"label": "2030", "value": 2030},
                        {"label": "2040", "value": 2040},
                    ],
                    placeholder="Prediction Year",
                    style={"marginBottom": "20px", "width": "80%"}
                ),
                # Aquí iría después tu gráfica, etc.
                html.Div(id="saltmarsh-chart")
            ])
        else:
            # Para otras pestañas, pones tu contenido actual
            return html.Div(f"Contenido de {tab}")
    @app.callback(
            Output("year-dropdown", "options"),
            Output("year-dropdown", "disabled"),
            Input("study-area-dropdown", "value")
        )
    def update_year_options(area):
        if area == "area1":
            years = [2017, 2067, 2117]
        elif area == "area2":
            years = [2012, 2062, 2112]
        elif area == "area3":
            years = [2022, 2072, 2122]
        else:
            return [], True
        opts = [{"label": str(y), "value": y} for y in years]
        return opts, False
    
# Luego, en el create_app():
# from .callbacks.tab_callbacks import register_tab_callbacks
# register_tab_callbacks(app)
