# app/callbacks/opsa_callbacks.py  # callbacks del tab Physical con 6 capas estáticas por clase

import dash  # framework Dash
from typing import List  # tipado de listas
from dash import Input, Output, State, html, dcc, dash_table  # componentes Dash
from dash.exceptions import PreventUpdate  # controlar no-actualizaciones
import dash_leaflet as dl  # Leaflet para Dash
import plotly.express as px

from app.models.opsa import compute_condition_mean, compute_summary_by_habitat_type  # función del modelo OPSA


# ---------------------------
# Utilidades (leyenda y split)
# ---------------------------

def _legend_item(color: str, label: str) -> html.Div:  # crear un ítem de leyenda con color sólido
    return html.Div(  # contenedor del ítem
        style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'marginBottom': '4px'},  # estilo
        children=[  # hijos
            html.Div(style={'width':'14px','height':'14px','background':color,'border':'1px solid #888'}),  # cuadrito color
            html.Span(label)  # texto del ítem
        ]
    )

def _legend_nodata() -> html.Div:  # crear ítem de leyenda para NoData
    return html.Div(  # contenedor
        style={'display':'flex','alignItems':'center','gap':'6px','marginBottom':'4px'},  # estilo
        children=[  # hijos
            html.Div(style={  # cuadrito con tramado
                'width':'14px','height':'14px',
                'backgroundImage':'repeating-linear-gradient(45deg, rgba(0,0,0,0) 0, rgba(0,0,0,0) 4px, rgba(0,0,0,0.35) 4px, rgba(0,0,0,0.35) 6px)',
                'border':'1px solid #000'
            }),
            html.Span("NoData")  # etiqueta
        ]
    )

def _build_legend() -> html.Div:  # construir la leyenda completa
    colors = ['#edf8e9','#bae4b3','#74c476','#31a354','#006d2c']  # paleta 5 clases (verde claro→oscuro)
    labels = ['Very low (0–1)','Low (1–2)','Medium (2–3)','High (3–4)','Very high (4–5)']  # etiquetas
    return html.Div(  # contenedor de leyenda
        children=[
            html.Div("Condition", style={'fontWeight':'bold','marginBottom':'6px'}),  # título
            _legend_nodata(),  # item NoData
            *[_legend_item(c, l) for c, l in zip(colors, labels)]  # items de clases
        ]
    )

def _split_geojson_by_class(geojson: dict, class_field: str = "condition_class") -> dict:  # dividir features por clase
    buckets = {i: {'type': 'FeatureCollection', 'features': []} for i in range(6)}  # crear 6 buckets (0..5)
    for f in geojson.get('features', []):  # recorrer features
        props = f.get('properties', {}) or {}  # obtener propiedades
        cls_raw = props.get(class_field, 0)  # leer clase
        try:  # intentar convertir a entero
            cls = int(cls_raw)  # a entero
        except Exception:  # si falla conversión
            cls = 0  # mandar a NoData
        cls = 0 if cls < 0 or cls > 5 else cls  # acotar a 0..5
        buckets[cls]['features'].append(f)  # añadir la feature al bucket
    return buckets  # devolver diccionario clase->FeatureCollection


# ---------------------------
# Registro de callbacks OPSA
# ---------------------------

def register_opsa_tab_callbacks(app: dash.Dash):  # registrar callbacks del tab Physical

    @app.callback(  # centrar mapa y poblar checklist al elegir área
        Output("map", "viewport", allow_duplicate=True),  # viewport (lo tocan más callbacks)
        Output("ec-dropdown", "options"),  # opciones del checklist
        Output("ec-dropdown", "disabled", allow_duplicate=True),  # disabled compartido
        Output('ec', 'hidden'),  # mostrar/ocultar panel EC
        Input("opsa-study-area", "value"),  # área seleccionada
        prevent_initial_call=True  # evitar disparo inicial
    )
    def center_and_zoom(area):  # centrar mapa y poblar EC
        DEFAULT = {"center": [48.912724, -1.141208], "zoom": 6}  # vista por defecto
        if not area:  # si no hay área
            return DEFAULT, [], True, True  # estado inicial

        mapping = {  # centros/zoom por área
            "Santander": ([43.553269, -3.71836], 11),
            "North_Sea": ([51.824025,  2.627373], 9),
            "Irish_Sea": ([53.741164, -4.608093], 9),
        }
        center, zoom = mapping.get(area, (DEFAULT["center"], DEFAULT["zoom"]))  # elegir vista

        if area == "Santander":  # EC en Santander
            ec = ['Angiosperms','Benthic macroinvertebrates','Intertidal macroalgae','Subtidal macroalgae','Benthic habitats']  # lista EC
        elif area == "North_Sea":  # EC en North Sea
            ec = ['Benthic habitats','Macrozoobenthos']  # lista EC
        elif area == "Irish_Sea":  # EC en Irish Sea
            ec = ['Benthic habitats','Macrozoobenthos','Demersal fish']  # lista EC
        else:  # otro caso
            ec = []  # vacío

        return {"center": center, "zoom": zoom}, ([{"label": str(y), "value": y} for y in ec]), False, False  # devolver estado

    @app.callback(  # habilitar/deshabilitar Run según selección
        Output("run-eva-button", "disabled", allow_duplicate=True),  # output compartido
        Input("ec-dropdown", "value"),  # valores seleccionados
        prevent_initial_call=True  # evitar disparo inicial
    )
    def toggle_run_button(selected: List[str]):  # conmutar Run
        return not bool(selected)  # deshabilitar si no hay selección

    @app.callback(  # ejecutar modelo y pintar 6 capas estáticas por clase (sin JS)
        Output("opsa-layer", "children", allow_duplicate=True),  # lista de capas a pintar
        Output("reset-eva-button", "disabled", allow_duplicate=True),  # habilitar Reset
        Output("opsa-study-area", "disabled", allow_duplicate=True),  # bloquear área
        Output("ec-dropdown", "disabled", allow_duplicate=True),  # bloquear checklist
        Output("run-eva-button", "disabled", allow_duplicate=True),  # bloquear Run
        Output("map", "viewport", allow_duplicate=True),  # ajustar viewport
        Output("opsa-legend", "children", allow_duplicate=True),  # poner leyenda
        Output("opsa-chart", "children", allow_duplicate=True), # agregar grafica/tabla
        Input("run-eva-button", "n_clicks"),  # clics en Run
        State("opsa-study-area", "value"),  # área seleccionada
        State("ec-dropdown", "value"),  # EC seleccionados
        prevent_initial_call=True  # evitar disparo inicial
    )
    def run_opsa(n, area, components):  # ejecutar y pintar
        if not (n and area and components):  # validar entradas
            raise PreventUpdate  # no actualizar

        # 1) Ejecutar modelo -> GeoJSON con 'condition', 'confidence' y 'condition_class'
        geojson, parquet_path = compute_condition_mean(  # llamar a la función del modelo
            study_area=area,  # área
            components=components,  # lista de EC
            out_field_condition="condition",  # campo condición
            out_field_confidence="confidence",  # campo confianza
            out_field_class="condition_class",  # campo clase discreta 0..5
            persist=True  # persistir en parquet
        )

        # 2) Dividir en 6 FeatureCollections por clase 0..5
        buckets = _split_geojson_by_class(geojson, class_field="condition_class")  # dividir
        # paleta por clase 1..5 (verde claro→oscuro)
        class_colors = {1:'#edf8e9', 2:'#bae4b3', 3:'#74c476', 4:'#31a354', 5:'#006d2c'}  # colores
        layers = []  # lista de capas a devolver

        # 2.1) Capa NoData (clase 0) con borde negro y relleno transparente
        if buckets[0]['features']:  # si hay features NoData
            layers.append(  # añadir capa
                dl.GeoJSON(  # capa GeoJSON
                    id="opsa-class-0",  # id de capa
                    data=buckets[0],  # solo features clase 0
                    options={"style": {"color": "black", "weight": 1, "dashArray": "4", "fillOpacity": 0.0}},  # estilo estático
                    zoomToBounds=False  # no forzar zoom con NoData
                )
            )

        # 2.2) Capas 1..5 con color sólido por clase
        for cls in (1, 2, 3, 4, 5):  # recorrer clases
            feats = buckets[cls]['features']  # obtener features de la clase
            if not feats:  # si no hay features
                continue  # saltar clase
            color = class_colors[cls]  # color para la clase
            layers.append(  # añadir capa
                dl.GeoJSON(  # capa GeoJSON
                    id=f"opsa-class-{cls}",  # id único
                    data=buckets[cls],  # features de la clase
                    options={"style": {"fillColor": color, "color": "#ffffff", "weight": 0.5, "fillOpacity": 0.75}},  # estilo sólido
                    zoomToBounds=True  # encuadrar al contenido
                )
            )

        # 3) Calcular viewport de respaldo (por si no se ajusta con zoomToBounds)
        try:  # intentar calcular bbox con todas las features
            coords = []  # lista de coordenadas
            for f in geojson.get("features", []):  # recorrer todas las features
                g = f.get("geometry")  # obtener geometría
                if not g:  # si no hay geometría
                    continue  # saltar
                def _walk(c):  # recorrido recursivo de coords
                    if isinstance(c[0], (float, int)):  # si es par [lon,lat]
                        coords.append(c)  # añadir coordenada
                    else:  # si es lista de listas
                        for cc in c:  # recorrer sublista
                            _walk(cc)  # recursión
                _walk(g.get("coordinates", []))  # iniciar recorrido
            lats = [p[1] for p in coords]  # lista de latitudes
            lons = [p[0] for p in coords]  # lista de longitudes
            viewport = {"center": [(min(lats)+max(lats))/2.0, (min(lons)+max(lons))/2.0], "zoom": 9} if (lats and lons) else dash.no_update  # viewport
        except Exception:  # ante cualquier error
            viewport = dash.no_update  # no tocar viewport

        # 4) Construir leyenda
        legend = _build_legend()  # crear leyenda

        # 5) Resumen por 'x' en tabla (modelo devuelve km² y promedios ponderados)
        try:  # intentar construir tabla
            df = compute_summary_by_habitat_type(parquet_path=parquet_path, study_area=area, group_field="AllcombD")  # obtener DF
            df_disp = df.copy()  # copiar para formateo
            df_disp["area_km"] = df_disp["area_km"].round(3)  # redondear área a 3 decimales
            df_disp["condition_wavg"] = df_disp["condition_wavg"].round(2)  # redondear condición a 2 decimales
            df_disp["confidence_wavg"] = df_disp["confidence_wavg"].round(2)  # redondear confianza a 2 decimales

            # renombrar columnas para cabecera clara
            df_disp = df_disp.rename(columns={
                "habitat_type": "Habitat type",
                "group": "Habitat type",
                "area_km": "Area (km²)",
                "condition_wavg": "Condition",
                "confidence_wavg": "Confidence"
            })

            # construir DataTable con ordenación y exportación CSV
            table = dash_table.DataTable(
                id="opsa-summary-table",  # id de la tabla
                columns=[{"name": c, "id": c} for c in df_disp.columns],  # columnas
                data=df_disp.to_dict("records"),  # filas
                sort_action="native",  # ordenable
                filter_action="native",  # sin filtro (puedes activar si quieres)
                page_action="none",  # sin paginación (tabla compacta)
                export_format="csv",  # permitir exportar
                export_headers="display",  # usar cabeceras visibles
                style_table={"maxHeight": "720px", "overflowY": "auto", "border": "1px solid #ddd", "borderRadius": "8px"},  # estilo contenedor
                style_cell= {"padding": "8px", "fontSize": "1.2rem", "textAlign": "center"},  # celdas
                style_header={"fontWeight": "bold", "backgroundColor": "#f7f7f7", "borderBottom": "1px solid #ccc"},  # cabecera
                style_data_conditional=[  # mejorar legibilidad
                    {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"}  # zebra
                ],
            )
            table_block = html.Div([html.Hr(), html.H4("Summary by Habitat type"), table], style={"marginTop":"8px"})  # bloque con título y tabla
        except Exception as e:  # si algo falla
            table_block = html.Div(f"Summary error: {e}", style={'color':'#b00020','fontStyle':'italic','padding':'8px'})  # mensaje de error

        # 5) Devolver capas + estado UI + leyenda
        return layers, False, True, True, True, viewport, legend, table_block  # devolver todo preparado

    @app.callback(  # resetear el tab Physical
        Output("opsa-layer", "children", allow_duplicate=True),  # limpiar capas
        Output("ec-dropdown", "value"),  # limpiar selección
        Output("ec-dropdown", "disabled", allow_duplicate=True),  # reactivar checklist
        Output("opsa-study-area", "disabled", allow_duplicate=True),  # reactivar área
        Output("run-eva-button", "disabled", allow_duplicate=True),  # deshabilitar Run hasta nueva selección
        Output("reset-eva-button", "disabled", allow_duplicate=True),  # deshabilitar Reset
        Output("map", "viewport", allow_duplicate=True),  # volver a vista por defecto
        Output("opsa-legend", "children", allow_duplicate=True),  # limpiar leyenda
        Output("ec", "hidden", allow_duplicate=True),
        Output("opsa-study-area", "value"),
        Output("opsa-chart", "children"),
        Input("reset-eva-button", "n_clicks"),  # clics en Reset
        prevent_initial_call=True  # evitar disparo inicial
    )
    def reset_opsa(n):  # limpiar todo
        if not n:  # si no hay clic
            raise PreventUpdate  # no actualizar
        default_view = {"center": [48.912724, -1.141208], "zoom": 6}  # viewport por defecto
        return [], [], False, False, True, True, default_view, [], True, "", []  # devolver estado limpio

    @app.callback(  # limpiar al cambiar de tab
        Output("opsa-legend", "children", allow_duplicate=True),  # limpiar leyenda
        Output("ec", "hidden", allow_duplicate=True),
        Output("opsa-layer", "children"),
        Input("tabs", "value"),  # tab activo
        prevent_initial_call=True  # evitar disparo inicial
    )
    def clear_on_tab_change(active_tab):  # limpiar si salimos del tab Physical
        if active_tab != "tab-physical":  # si no estamos en Physical
            return [], True, [] # dejar leyenda vacía
        raise PreventUpdate  # si seguimos en Physical, no tocar
