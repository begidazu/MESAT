from dash.dependencies import Input, Output, State
from dash import html, dcc
from app.models.model_a import run as run_model_a
from app.models.model_b import run as run_model_b

def register_model_callbacks(app):
    @app.callback(
        Output('model-output', 'children'),
        Input('run-button', 'n_clicks'),
        State('model-checklist', 'value')
    )
    def _run_models(n_clicks, selected_models):
        # Aquí va la lógica para ejecutar modelos y devolver html.Div con resultados
        return []
