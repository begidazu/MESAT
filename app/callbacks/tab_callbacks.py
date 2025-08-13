import os, glob  # manejar rutas y buscar archivos
import io  # buffers en memoria
from zipfile import ZipFile  # crear ZIPs
import dash_leaflet as dl  # componentes Leaflet
import rasterio  # lectura ráster
from rasterio.vrt import WarpedVRT  # reproyección al vuelo
from rasterio.enums import Resampling  # remuestreo
from dash import Input, Output, State, html, dcc, callback_context  # Dash core
import dash  # tipado de la app
from dash.exceptions import PreventUpdate  # evitar actualizaciones
import dash_bootstrap_components as dbc  # componentes Bootstrap
from matplotlib.colors import ListedColormap, BoundaryNorm  # colores matplotlib
import matplotlib.pyplot as plt  # dibujar PNGs
import plotly.express as px  # gráficas interactivas
import numpy as np  # numérico
import time

# =============================
# Constantes y utilidades
# =============================

CLASS_INFO = {  # mapa valor->(etiqueta,color)
    0: ("Mudflat", "#8B4513"),
    1: ("Saltmarsh", "#006400"),
    2: ("Upland Areas", "#636363"),
    3: ("Channel", "#31C2F3")
}
LABEL_TO_COLOR = {name: color for _, (name, color) in CLASS_INFO.items()}  # etiqueta->color
CATEGORY_ORDER = [CLASS_INFO[k][0] for k in sorted(CLASS_INFO.keys())]  # orden fijo de categorías

BTN_STYLE = {  # estilo común de botones
    'padding': '10px', 'marginTop': '20px', 'borderRadius': '6px',
    'display': 'flex', 'alignItems': 'center', 'gap': '8px',
    'fontSize': '14px', 'fontWeight': '600'
}

def _acc_tif_from_class_tif(class_tif):  # localizar tif de acreción emparejado
    base, ext = os.path.splitext(class_tif)  # separar base y extensión
    acc_path = f"{base}_accretion{ext}"  # ruta esperada exacta
    if os.path.exists(acc_path):  # si existe el esperado
        return acc_path  # devolver ruta
    folder = os.path.dirname(class_tif)  # carpeta del tif de clases
    stem = os.path.basename(base)  # nombre base sin extensión
    hits = glob.glob(os.path.join(folder, f"{stem}*_accretion{ext}"))  # buscar variantes
    return hits[0] if hits else None  # devolver primera coincidencia o None

def _find_class_tif(area, scen, year):  # localizar tif de clases por área/escenario/año
    base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # ruta base
    if not os.path.isdir(base):  # comprobar existencia de carpeta
        return None  # no hay datos
    hits = glob.glob(os.path.join(base, f"*{year}*.tif")) + glob.glob(os.path.join(base, f"*{year}*.tiff"))  # candidatos por año
    hits = [p for p in hits if "accretion" not in os.path.basename(p).lower()]  # excluir *_accretion.*
    return sorted(hits)[0] if hits else None  # devolver primero o None

def _areas_por_habitat(tif_path):  # sumar áreas (ha) por clase
    with rasterio.open(tif_path) as src:  # abrir tif
        arr = src.read(1)  # leer banda 1
        resx, resy = src.res  # resolución de píxel
    pixel_area_m2 = float(abs(resx * resy))  # área de píxel en m²
    valores, cuentas = np.unique(arr, return_counts=True)  # contar por valor
    areas_ha = [float(c * pixel_area_m2 / 10000.0) for v, c in zip(valores, cuentas) if v in CLASS_INFO]  # pasar a ha
    etiquetas = [CLASS_INFO[v][0] for v in valores if v in CLASS_INFO]  # etiquetas legibles
    colores = [CLASS_INFO[v][1] for v in valores if v in CLASS_INFO]  # colores por clase
    return etiquetas, areas_ha, colores  # devolver resultados

def _png_grafico_areas(titulo, etiquetas, valores, colores):  # crear PNG de barras (áreas)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)  # figura
    bars = ax.bar(etiquetas, valores, color=colores)  # barras
    ax.set_title(titulo)  # título
    ax.set_xlabel("Habitat")  # eje X
    ax.set_ylabel("Area (ha)")  # eje Y
    ax.grid(True, alpha=0.3)  # rejilla
    ymax = max(valores) if valores else 0  # máximo
    ax.set_ylim(0, ymax*1.15 if ymax else 1)  # margen superior
    for b, v in zip(bars, valores):  # anotar valores
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.2f}",
                ha="center", va="bottom", fontweight="bold", fontsize=12)
    buf = io.BytesIO()  # buffer
    fig.tight_layout()  # ajustar
    fig.savefig(buf, format="png")  # guardar PNG
    plt.close(fig)  # cerrar
    buf.seek(0)  # rebobinar
    return buf  # devolver buffer

def _accretion_volume_by_class(class_tif, acc_tif):  # calcular volumen acumulado por clase
    with rasterio.open(class_tif) as cls:  # abrir clases
        class_arr = cls.read(1)  # leer banda
    with rasterio.open(acc_tif) as acc:  # abrir acreción
        acc_arr = acc.read(1, masked=True)  # leer con máscara de nodata
        resx, resy = acc.res  # resolución
        pixel_area_m2 = abs(resx * resy)  # área de píxel
    if class_arr.shape != acc_arr.shape:  # validar alineación
        raise ValueError("Class raster and accretion raster are not aligned.")  # error si no coinciden
    acc_filled = np.ma.filled(acc_arr, 0.0)  # rellenar nodata con 0
    sums = np.bincount(class_arr.ravel(), weights=acc_filled.ravel(), minlength=4)  # sumar por clase
    etiquetas, valores = [], []  # listas de salida
    for v in sorted(CLASS_INFO.keys()):  # recorrer clases
        vol_m3 = float(sums[v] * pixel_area_m2)  # convertir a volumen
        if abs(vol_m3) > 1e-9:  # ignorar cero exacto
            etiquetas.append(CLASS_INFO[v][0])  # añadir etiqueta
            valores.append(vol_m3)  # añadir valor
    return etiquetas, valores  # devolver resultados

def _png_grafico_accretion(titulo, etiquetas, valores):  # crear PNG de acreción
    colores = [LABEL_TO_COLOR[e] for e in etiquetas]  # colores por etiqueta
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)  # figura
    bars = ax.bar(etiquetas, valores, color=colores)  # barras
    ax.set_title(titulo)  # título
    ax.set_xlabel("Habitat")  # eje X
    ax.set_ylabel("Accretion volume (m³)")  # eje Y
    ax.grid(True, alpha=0.3)  # rejilla
    ymax = max(valores) if valores else 0  # máximo
    ax.set_ylim(0, ymax*1.15 if ymax else 1)  # margen
    for b, v in zip(bars, valores):  # anotar valores
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.2f}",
                ha="center", va="bottom", fontweight="bold", fontsize=12)
    buf = io.BytesIO()  # buffer
    fig.tight_layout()  # ajustar
    fig.savefig(buf, format="png")  # guardar
    plt.close(fig)  # cerrar
    buf.seek(0)  # rebobinar
    return buf  # devolver

# =============================
# Registro de callbacks
# =============================

def register_tab_callbacks(app: dash.Dash):  # registrar callbacks
    SCENARIOS = [  # lista de escenarios (carpeta, etiqueta)
        ("regional_rcp45", "Regional RCP4.5"),
        ("regional_rcp85", "Regional RCP8.5"),
        ("global_rcp45",  "Global RCP4.5"),
    ]

    @app.callback(  # render del tab saltmarsh
        Output("tab-content", "children"),
        Input("tabs", "value")
    )
    def render_tab(tab):  # función de renderizado
        if tab != "tab-saltmarsh":  # si no es el tab objetivo
            return html.Div(f"Contenido de {tab}")  # devolver marcador
        return html.Div([  # UI del tab
            html.Div(  # panel de selects y botones
                style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},  # estilos
                children=[  # hijos del panel
                    dcc.Dropdown(  # selector de área
                        id="study-area-dropdown",  # id
                        options=[  # opciones
                            {"label":"Urdaibai Estuary","value":"Urdaibai_Estuary"},
                            {"label":"Bay of Santander","value":"Bay_of_Santander"},
                            {"label":"Cadiz Bay","value":"Cadiz_Bay"},
                        ],
                        placeholder="Select Study Area",  # ayuda
                        className='dropdown-text'  # clase css
                    ),
                    dcc.Dropdown(  # selector de año
                        id="year-dropdown",  # id
                        options=[],  # sin opciones hasta elegir área
                        placeholder="Year",  # ayuda
                        className="dropdown-text",  # clase css
                        disabled=True  # deshabilitado hasta elegir área
                    ),
                    html.Div(  # fila de botones
                        style={'display':'flex','gap':'10px','alignItems':'center'},  # estilos
                        children=[  # hijos
                            html.Button(  # botón Run
                                html.Span("Run"),  # texto
                                id="run-button",  # id
                                n_clicks=0,  # contador
                                disabled=True,  # deshabilitado al inicio
                                className='btn btn-outline-primary'  # clase css
                                #style={'width':'100px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}  # estilo
                            ),
                            html.Button(  # botón Reset
                                html.Span("Restart"),  # texto
                                id="reset-button",  # id
                                n_clicks=0,  # contador
                                className='btn btn-outline-primary',  # clase css
                                disabled=True  # deshabilitado al inicio
                            )
                        ]
                    ),

                    html.Div(
                        id='scenario-checklist-div',
                        hidden = True,
                        children=[
                            html.Legend(
                                "Select Climate Change Scenario Map",
                                className="mt-4"  # aquí la clase que quieras (Bootstrap o CSS propio)
                            ),
                            dcc.RadioItems(
                                id='scenario-radio',
                                options=[
                                    {'label': 'Regional RCP4.5', 'value': 'reg45'},
                                    {'label': 'Regional RCP8.5', 'value': 'reg85'},
                                    {'label': 'Global RCP4.5',  'value': 'glo45'},
                                ],
                                value='reg45',
                                inline=False,
                                inputClassName= 'form-check-input',
                                className= 'form-check',
                                labelClassName= 'form-check-label'

                                
                            )
                        ]
                    )
                ]
            ),
            dcc.Loading(  # contenedor con spinner
                id="loading",  # id
                type="circle",  # tipo de spinner
                children=[  # hijos
                    html.Legend("Habitat distribution and accretion statistics", className='mt-4', id='saltmarsh-legend', hidden=True),
                    html.Div(id="saltmarsh-chart", style={'marginTop':'20px'}),  # contenedor de gráficas
                    html.Div(  # barra inferior
                        id='button-bar',  # id
                        style={'display':'flex','justifyContent':'center','alignItems':'center','verticalAlign':'middle','gap':'12px'},  # estilos
                        children=[  # hijos
                            html.Button(  # botón info
                                [html.Img(src='/assets/logos/info.png', style={'width':'20px','height':'20px'}), html.Span("Habitat and accretion info")],  # contenido
                                id='info-button',  # id
                                className='btn btn-outline-primary',
                                hidden=True,  # oculto al inicio
                                n_clicks=0  # contador
                            ),
                            html.Div(  # contenedor de descarga
                                [
                                    html.Button(  # botón de descarga
                                        [html.Img(src='/assets/logos/download.png', style={'width':'20px','height':'20px'}), html.Span("Download results")],  # contenido
                                        id='marsh-results',  # id
                                        hidden=True,  # oculto al inicio
                                        n_clicks=0,  # contador
                                        className='btn btn-outline-primary'
                                    ),
                                    dcc.Download(id='saltmarsh-download')  # componente de descarga
                                ]
                            )
                        ]
                    )
                ]
            ),
            dbc.Modal(  # modal de información
                [
                    dbc.ModalHeader(dbc.ModalTitle("Habitat & accretion information")),  # cabecera
                    dbc.ModalBody(  # cuerpo
                        html.Ul([
                                html.Li([html.B("Mudflat: "), html.I("Mudflats")," represent an important part of coastal wetlands, which, like marshes, provide a wide range of ecosystem services such as coastal defence and carbon sequestration."]),  # info Mudflat
                                html.Li([html.B("Saltmarsh: "), html.I("Saltmarshes"), " are coastal wetlands characterized by its low-lying, flat, and poorly drained soil that is regularly or occasionally flooded by salty or brackish water. Like Mudflats, saltmarshes provide a wide range of ecosystem services such as coastal defence, carbon sequestration and food provisioning."]),  # info Saltmarsh
                                html.Li([html.B("Upland Areas: "), html.I("Upland Areas"), " represent non-flooded areas where marshes can migrate during sea level rise conditions."]),  # info Upland
                                html.Li([html.B("Channel: "), html.I("Channels"), " are key features of wetlands that control fundamental dynamics like sediment availability, nutrient circulation and hydrodynamics."]),  # info Channel
                                html.Li([html.B("Accretion: "), html.I("Accretion"), " is the process where the elevation of a saltmarsh surface increases over time, either by the accumulation of mineral sediments (like silt and clay) or by the buildup of organic matter from decaying plant material. Through ", html.I("accretion"), ", saltmarshes sequester carbon from both accumulation of mineral sediments and organic matter from decaying plant material. "]) # info Accretion
                        ])
                    ),
                    dbc.ModalFooter(dbc.Button("Close", id="info-close", className="ml-auto", n_clicks=0))  # pie
                ],
                id="info-modal", is_open=False, size="lg", centered=True, backdrop=True  # props
            )
        ], style={'padding':'20px'})  # padding general

    @app.callback(  # poblar años según área
        Output("year-dropdown","options"),
        Output("year-dropdown","disabled"),
        Input("study-area-dropdown","value")
    )
    def update_year_options(area):  # actualizar años
        if area=="Urdaibai_Estuary": years=[2017,2067,2117]
        elif area=="Bay_of_Santander": years=[2012,2062,2112]
        elif area=="Cadiz_Bay": years=[2023,2073,2123]
        else: return [], True
        return ([{"label":str(y),"value":y} for y in years], False)

    @app.callback(  # centrar/zoom por área
        Output("map", "viewport"),
        Input("study-area-dropdown", "value")
    )
    def center_and_zoom(area):  # cambiar viewport
        if not area:
            raise PreventUpdate
        mapping = {
            "Urdaibai_Estuary": ([43.364580815052316, -2.67957208131426804], 14),
            "Bay_of_Santander": ([43.43984351219931,  -3.7526739449807447], 15),
            "Cadiz_Bay":        ([36.520874060327226, -6.203490800462997],  15)
        }
        center, zoom = mapping[area]
        return {"center": center, "zoom": zoom}

    @app.callback(  # habilitar Run cuando hay área y año
        Output("run-button","disabled", allow_duplicate=True),
        Input("study-area-dropdown","value"),
        Input("year-dropdown","value"),
        prevent_initial_call=True
    )
    def toggle_run(area, year):  # conmutar estado de Run
        return not (area and year)

    @app.callback(  # pintar overlays para 3 escenarios
        Output("reg-rcp45","children", allow_duplicate=True),
        #Output("raster-layer-regional_rcp85","children", allow_duplicate=True),
        #Output("raster-layer-global_rcp45","children",  allow_duplicate=True),
        Output("reset-button", "disabled", allow_duplicate=True),
        Output("study-area-dropdown", "disabled", allow_duplicate=True),
        Output("year-dropdown", "disabled", allow_duplicate=True),
        Output("run-button", "disabled"),
        Output('marsh-results', 'hidden'),
        Input("run-button","n_clicks"),
        State("study-area-dropdown","value"),
        State("year-dropdown","value"),
        prevent_initial_call=True
    )
    def update_map(n, area, year):  # añadir overlays
        if not (n and area and year):
            return [], [], [], True, False, False, True, True
        
        scen = 'regional_rcp45'
        tif_dir = os.path.join(os.getcwd(),"results","saltmarshes",area,scen)  # construir ruta al directorio de TIFs
        matches = glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))  # buscar el TIF del año
        if not matches:  # comprobar que existe el TIF
            raise PreventUpdate  # no actualizar si no hay datos
        m = matches[0]  # tomar el primer TIF disponible
        with rasterio.open(m) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:  # abrir y reproyectar a WGS84 para bounds
            data = vrt.read(1,masked=True)  # leer banda como masked
            import numpy as np  # importar numpy localmente para enmascarado
            data = np.ma.masked_where(data.data==0,data)  # enmascarar clase 0 como nodata por coherencia visual
            b = vrt.bounds  # extraer límites geográficos
        url = f"/raster/{area}/{scen}/{year}.png"  # construir URL del PNG servido por Flask
        overlay = dl.ImageOverlay(url=url,bounds=[[b.bottom, b.left], [b.top, b.right]],opacity=1)  # crear capa de imagen
        return overlay, False, True, True, True, False  # estados de UI

    @app.callback(  # reset total
        Output("study-area-dropdown", "value", allow_duplicate=True),
        Output("study-area-dropdown", "disabled", allow_duplicate=True),
        Output("year-dropdown", "value", allow_duplicate=True),
        Output("year-dropdown", "disabled", allow_duplicate=True),
        Output("reg-rcp45", "children", allow_duplicate=True),
        Output("saltmarsh-chart", "children", allow_duplicate=True),
        Output('info-button', 'hidden', allow_duplicate=True),
        Output('marsh-results', 'hidden', allow_duplicate=True),
        Output('reset-button', 'disabled', allow_duplicate=True),
        Output('scenario-checklist-div', 'hidden', allow_duplicate=True),
        Output('saltmarsh-legend', 'hidden', allow_duplicate=True),
        # Output('scenario-checklist', 'value'),
        Output('scenario-radio', 'value'),
        Input("reset-button", "n_clicks"),
        prevent_initial_call=True
    )
    def reset(n):  # limpiar todo
        if n:
            return [None, False, None, True, [], [], True, True, True, True, 'reg45', True]
        raise PreventUpdate

    @app.callback(  # gráficas con sub-tabs por escenario
        Output("saltmarsh-chart", "children"),
        Output('info-button', "hidden"),
        Output('marsh-results', 'hidden', allow_duplicate=True),
        Output("reset-button", "disabled"),
        Output('scenario-checklist-div', 'hidden'),
        Output('saltmarsh-legend','hidden'),
        Input("run-button", "n_clicks"),
        State("study-area-dropdown", "value"),
        State("year-dropdown", "value"),
        prevent_initial_call=True
    )
    def update_saltmarsh_chart(n, area, year):  # construir gráficas
        if not (n and area and year):
            raise PreventUpdate

        def class_tif(area, scen, year):  # localizar tif de clases
            base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # carpeta base
            hits = glob.glob(os.path.join(base, f"*{year}*.tif")) + glob.glob(os.path.join(base, f"*{year}*.tiff"))  # candidatos
            hits = [p for p in hits if "accretion" not in os.path.basename(p).lower()]  # excluir acreción
            return sorted(hits)[0] if hits else None  # devolver primero o None

        def fig_areas_from_tif(tif_path):  # figura de áreas
            etiquetas, areas_ha, _ = _areas_por_habitat(tif_path)  # sumar áreas
            fig = px.bar(  # barplot
                x=etiquetas, y=areas_ha, title="<b>Habitat Areas (ha)</b>",
                color=etiquetas, color_discrete_map=LABEL_TO_COLOR
            )
            fig.update_traces(texttemplate='<b>%{y:.2f}</b>', textposition='outside', cliponaxis=False)  # etiquetas
            fig.update_layout(showlegend=False, xaxis_title="<b>Habitat</b>", yaxis_title="<b>Area (ha)</b>",
                              title_x=0.5, title_font_family="Garamond", title_font_size=25,
                              uniformtext_minsize=10, uniformtext_mode='show')  # layout
            fig.update_xaxes(categoryorder='array', categoryarray=CATEGORY_ORDER)  # orden
            return fig  # devolver figura

        def fig_acc_from_pair(class_tif_path):  # figura de acreción
            acc_tif = _acc_tif_from_class_tif(class_tif_path)  # localizar accretion
            if not acc_tif:  # si no existe
                return html.Div("No accretion raster found in this scenario folder.", style={"color":"#555","fontStyle":"italic"})  # mensaje
            etiquetas_acc, valores_acc = _accretion_volume_by_class(class_tif_path, acc_tif)  # calcular volúmenes
            if not valores_acc:  # si vacío
                return html.Div("No non-zero accumulated accretion found for this scenario.", style={"color":"#555","fontStyle":"italic"})  # mensaje
            fig = px.bar(  # barplot
                x=etiquetas_acc, y=valores_acc, title="<b>Accumulated Accretion (m³) by habitat</b>",
                color=etiquetas_acc, color_discrete_map=LABEL_TO_COLOR
            )
            y_max = max(valores_acc)  # máximo
            fig.update_traces(texttemplate='<b>%{y:.2f}</b>', textposition='outside', textfont_size=14, cliponaxis=False)  # etiquetas
            fig.update_layout(showlegend=False, xaxis_title="<b>Habitat</b>", yaxis_title="<b>Accretion volume (m³)</b>",
                              title_x=0.5, title_font_family="Garamond", title_font_size=25,
                              yaxis_range=[0, y_max*1.2 if y_max else 1],
                              uniformtext_minsize=10, uniformtext_mode='show')  # layout
            fig.update_xaxes(categoryorder='array', categoryarray=CATEGORY_ORDER)  # orden
            return dcc.Graph(figure=fig, config={"modeBarButtonsToRemove": ["zoom2d","pan2d","zoomIn2d","zoomOut2d","lasso2d","resetScale2d"]})  # componente Graph

        area_tabs_children, acc_tabs_children = [], []  # listas de tabs
        first_value = None  # valor inicial seleccionado

        for scen, scen_label in SCENARIOS:  # recorrer escenarios
            tif_path = class_tif(area, scen, year)  # localizar tif
            if not tif_path:  # si no hay datos
                area_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[html.Div("No class raster found for this scenario/year.", style={"color":"#555","fontStyle":"italic"})]))  # tab vacío
                acc_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[html.Div("No accretion raster found for this scenario/year.", style={"color":"#555","fontStyle":"italic"})]))  # tab vacío
                continue  # siguiente escenario

            fig_areas = fig_areas_from_tif(tif_path)  # construir figura
            area_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[dcc.Graph(figure=fig_areas, config={"modeBarButtonsToRemove": ["zoom2d","pan2d","zoomIn2d","zoomOut2d","lasso2d","resetScale2d"]})]))  # tab con figura
            acc_content = fig_acc_from_pair(tif_path)  # contenido de acreción
            acc_tabs_children.append(dcc.Tab(label=scen_label, value=scen, children=[acc_content]))  # tab de acreción

            if first_value is None:  # fijar tab inicial
                first_value = scen  # seleccionar este

        if first_value is None:  # si ningún escenario tenía datos
            first_value = SCENARIOS[0][0]  # usar primero por defecto

        charts = dcc.Tabs(  # tabs principales
            id="saltmarsh-inner-tabs",  # id de tabs
            value="areas",  # seleccionar áreas
            children=[  # dos pestañas principales
                dcc.Tab(  # pestaña de áreas
                    label='Habitat Areas',  # etiqueta
                    value='areas',  # valor
                    children=[dcc.Tabs(id="areas-by-scen", value=first_value, children=area_tabs_children)]  # sub-tabs por escenario
                ),
                dcc.Tab(  # pestaña de acreción
                    label='Accumulated Accretion',  # etiqueta
                    value='accretion',  # valor
                    children=[dcc.Tabs(id="accretion-by-scen", value=first_value, children=acc_tabs_children)]  # sub-tabs por escenario
                )
            ]
        )
        return [charts, False, False, False, False, False]  # devolver UI y mostrar botón info

    @app.callback(  # descarga ZIP por escenario
        Output('saltmarsh-download', 'data'),
        Input('marsh-results', 'n_clicks'),
        State("study-area-dropdown", "value"),
        State("year-dropdown", "value"),
        prevent_initial_call=True
    )
    def download_results(n, area, year):  # construir zip
        if not (n and area and year):
            raise PreventUpdate

        def class_tif(area, scen, year):  # helper localizar tif de clases
            base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # ruta base
            hits = glob.glob(os.path.join(base, f"*{year}*.tif")) + glob.glob(os.path.join(base, f"*{year}*.tiff"))  # candidatos
            hits = [p for p in hits if "accretion" not in os.path.basename(p).lower()]  # excluir acreción
            return sorted(hits)[0] if hits else None  # primero o None

        zip_buf = io.BytesIO()  # buffer del zip
        with ZipFile(zip_buf, 'w') as zf:  # abrir zip
            for scen, _ in SCENARIOS:  # recorrer escenarios
                tif_path = class_tif(area, scen, year)  # localizar tif
                if not tif_path:  # si no existe
                    continue  # saltar
                etiquetas, areas_ha, colores = _areas_por_habitat(tif_path)  # calcular áreas
                titulo = f"Habitat Areas — {area} / {scen} / {year}"  # título
                png_buf = _png_grafico_areas(titulo, etiquetas, areas_ha, colores)  # generar PNG
                zf.writestr(f"{scen}/habitat_areas_{area}_{scen}_{year}.png", png_buf.getvalue())  # añadir PNG
                zf.write(tif_path, arcname=f"{scen}/{os.path.basename(tif_path)}")  # añadir TIF de clases
                acc_tif = _acc_tif_from_class_tif(tif_path)  # localizar accretion
                if acc_tif and os.path.exists(acc_tif):  # si existe
                    try:  # intentar PNG de acreción
                        etiquetas_acc, valores_acc = _accretion_volume_by_class(tif_path, acc_tif)  # calcular volúmenes
                        if valores_acc:  # si hay datos
                            titulo_acc = f"Accumulated Accretion — {area} / {scen} / {year}"  # título
                            acc_png_buf = _png_grafico_accretion(titulo_acc, etiquetas_acc, valores_acc)  # generar PNG
                            zf.writestr(f"{scen}/accumulated_accretion_{area}_{scen}_{year}.png", acc_png_buf.getvalue())  # añadir PNG
                    except Exception:  # silenciar errores de cálculo
                        pass  # continuar
                    zf.write(acc_tif, arcname=f"{scen}/{os.path.basename(acc_tif)}")  # añadir TIF de accretion
        zip_buf.seek(0)  # rebobinar
        return dcc.send_bytes(lambda f: f.write(zip_buf.getvalue()), filename=f"saltmarsh_results_{area}_{year}.zip")  # devolver zip

    @app.callback(  # toggle modal info
        Output("info-modal", "is_open"),
        Input("info-button", "n_clicks"),
        Input("info-close",  "n_clicks"),
        State("info-modal",  "is_open"),
        prevent_initial_call=True
    )
    def toggle_info_modal(open_clicks, close_clicks, is_open):  # alternar modal
        ctx = callback_context  # contexto
        if not ctx.triggered:  # si no hay disparador
            raise PreventUpdate  # no actualizar
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]  # id del disparador
        if trigger in ["info-button", "info-close"]:  # si es abrir/cerrar
            return not is_open  # alternar
        return is_open  # mantener

    
    # Callback para dar funcionalidad al scenario checklist:
    @app.callback(
        Output('reg-rcp45','children', allow_duplicate=True),  # tu contenedor de capas
        Input('scenario-radio','value'),
        State('study-area-dropdown','value'),
        State('year-dropdown','value'),
        prevent_initial_call=True
    )
    def scenario_overlay(selected, area, year):
        if not (area and year and selected):
            raise PreventUpdate
        scen_map = {'reg45':'regional_rcp45','reg85':'regional_rcp85','glo45':'global_rcp45'}
        scen = scen_map[selected]
        base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)
        matches = sorted(glob.glob(os.path.join(base, f"*{year}*.tif")))
        if not matches:
            return []
        with rasterio.open(matches[0]) as src, WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.nearest) as vrt:
            b = vrt.bounds
        url = f"/raster/{area}/{scen}/{year}.png?ts={int(time.time())}"
        return [dl.ImageOverlay(id=f"overlay-{scen}", url=url,
                                bounds=[[b.bottom,b.left],[b.top,b.right]], opacity=1)]