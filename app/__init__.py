from dash import Dash
from .layout import create_layout
from .callbacks.models_callbacks import register_model_callbacks
from .callbacks.draw_callbacks import register_draw_callbacks
from .callbacks.tab_callbacks import register_tab_callbacks
import dash_bootstrap_components as dbc

def create_app():
    app = Dash(
        __name__, 
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        title = "PhD Web Application"
        )
    app.layout = create_layout()
    register_model_callbacks(app)
    register_draw_callbacks(app)
    register_tab_callbacks(app)
    return app