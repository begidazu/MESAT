from dash import Dash
from .layout import create_layout
from .callbacks.draw_callbacks import register_draw_callbacks
from .callbacks.marsh_callbacks import register_tab_callbacks
from .callbacks.opsa_callbacks import register_opsa_tab_callbacks
from .callbacks.management_callbacks import register_management_callbacks
from .callbacks.eva_mpaeu_callbacks import register_eva_mpaeu_callbacks
from .callbacks.fish_stock_callbacks import register_fish_stock_callbacks
import dash_bootstrap_components as dbc

import diskcache
from dash import Dash, DiskcacheManager

def create_app():

    cache = diskcache.Cache("./cache_directorio")
    background_manager = DiskcacheManager(cache)

    app = Dash(
        __name__, 
        background_callback_manager=background_manager,
        external_stylesheets=[dbc.themes.FLATLY, "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"],
        suppress_callback_exceptions=True,
        title = "Marine Ecosystem & Services Impact Tool (MESIT)"
        )
    app.layout = create_layout()
    register_draw_callbacks(app)
    register_tab_callbacks(app)
    register_opsa_tab_callbacks(app)
    register_management_callbacks(app)
    register_eva_mpaeu_callbacks(app)
    register_fish_stock_callbacks(app)
    return app