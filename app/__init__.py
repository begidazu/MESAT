from dash import Dash
from .layout import create_layout
from .callbacks.models_callbacks import register_model_callbacks
from .callbacks.draw_callbacks import register_draw_callbacks

def create_app():
    app = Dash(__name__)
    app.layout = create_layout()
    register_model_callbacks(app)
    register_draw_callbacks(app)
    return app