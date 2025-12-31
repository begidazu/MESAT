from dash import Dash
from .layout import create_layout
from .callbacks.models_callbacks import register_model_callbacks
from .callbacks.draw_callbacks import register_draw_callbacks
from .callbacks.marsh_callbacks import register_tab_callbacks
from .callbacks.opsa_callbacks import register_opsa_tab_callbacks
from .callbacks.management_callbacks import register_management_callbacks
from .callbacks.eva_mpaeu_callbacks import register_eva_mpaeu_callbacks
import dash_bootstrap_components as dbc

def create_app():
    app = Dash(
        __name__, 
        external_stylesheets=[dbc.themes.FLATLY, "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"],
        suppress_callback_exceptions=True,
        title = "PhD Web Application"
        )
    app.layout = create_layout()
    register_model_callbacks(app)
    register_draw_callbacks(app)
    register_tab_callbacks(app)
    register_opsa_tab_callbacks(app)
    register_management_callbacks(app)
    register_eva_mpaeu_callbacks(app)
    return app