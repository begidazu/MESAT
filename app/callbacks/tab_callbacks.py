import os, glob
import io  # importar io para manejar buffers en memoria (BytesIO)
from zipfile import ZipFile  # importar ZipFile para crear un ZIP con múltiples resultados
from datetime import datetime  # importar datetime para estampar fecha en nombres de archivo
import dash_leaflet as dl
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import rowcol
from dash import Input, Output, State, html, dcc, callback_context
import dash
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash_bootstrap_components import Spinner, Button, ButtonGroup
from matplotlib.colors import ListedColormap,BoundaryNorm
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
 

# =============================
# Constantes y utilidades
# =============================

# Diccionario de clases de hábitat y colores coherente en toda la app (evita ambigüedades con el valor 0)
CLASS_INFO = {  # definir nombres y colores por clase
    0: ("Mudflat", "#8B4513"),       # clase 1 → Mudflat con color marrón
    1: ("Saltmarsh", "#006400"),     # clase 2 → Saltmarsh con color verde oscuro
    2: ("Upland Areas", "#636363"),  # clase 3 → Upland Areas con color gris
    3: ("Channel", "#31C2F3")       # clase 4 → Channel con color azul
}

# Diccionario nombre → color para usar en plotly (asegura que no cambie la paleta)
LABEL_TO_COLOR = {name: color for _, (name, color) in CLASS_INFO.items()}  # construir mapeo etiqueta→color

# Orden de categorías fijo para ejes y leyendas
CATEGORY_ORDER = [CLASS_INFO[k][0] for k in sorted(CLASS_INFO.keys())]  # construir orden ['Mudflat','Saltmarsh','Upland Areas','Channel']

# Estilo base para botones de acción (Info y Download) para unificar tamaño/fuente/iconos
BTN_STYLE = {  # definir estilo común para botones de acción
    'padding': '10px',  # espaciado interno
    'marginTop': '20px',  # margen superior
    'borderRadius': '6px',  # esquinas redondeadas
    'display': 'flex',  # usar flex para alinear icono+texto
    'alignItems': 'center',  # alinear verticalmente
    'gap': '8px',  # separación entre icono y texto
    'fontSize': '14px',  # tamaño de fuente
    'fontWeight': '600'  # peso de fuente
}

# Localiza el tif de acrecion:
def _acc_tif_from_class_tif(class_tif):
    base, ext = os.path.splitext(class_tif)
    acc_path = f"{base}_accretion{ext}"
    if os.path.exists(acc_path):
        return acc_path
    # Fallback por si el nombre no es exacto
    folder = os.path.dirname(class_tif)
    stem = os.path.basename(base)
    hits = glob.glob(os.path.join(folder, f"{stem}*_accretion{ext}"))
    return hits[0] if hits else None

# Función auxiliar: localizar el TIF de clasificación para un área/escenario/año
def _find_class_tif(area, scen, year):  # definir función para buscar el ráster de clases
    base = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # construir ruta base a resultados
    if not os.path.isdir(base):  # comprobar que la carpeta existe
        return None  # devolver None si no existe
    matches = glob.glob(os.path.join(base, f"*{year}*.tif"))  # buscar TIF que contenga el año en el nombre
    return matches[0] if matches else None  # devolver la primera coincidencia o None

# Función auxiliar: resumir áreas por clase en hectáreas desde un ráster de clases
def _areas_por_habitat(tif_path):  # definir función para calcular áreas por hábitat
    with rasterio.open(tif_path) as src:  # abrir el ráster
        arr = src.read(1)  # leer banda 1 como matriz
        resx, resy = src.res  # obtener resolución de píxel (ancho, alto) en unidades del CRS
    pixel_area_m2 = abs(resx * resy)  # calcular área de cada píxel en m² (valor absoluto por seguridad)
    valores, cuentas = np.unique(arr, return_counts=True)  # contar píxeles por valor de clase
    clases_validas = [v for v in valores if v in CLASS_INFO]  # filtrar sólo clases definidas
    areas_ha = [float(c * pixel_area_m2 / 10000.0) for v, c in zip(valores, cuentas) if v in CLASS_INFO]  # convertir m² a ha
    etiquetas = [CLASS_INFO[v][0] for v in clases_validas]  # construir etiquetas legibles
    colores = [CLASS_INFO[v][1] for v in clases_validas]  # construir lista de colores por clase
    return etiquetas, areas_ha, colores  # devolver resultados

def _png_grafico_areas(titulo, etiquetas, valores, colores):  # definir función para crear PNG del barplot en servidor
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)  # crear figura de tamaño razonable
    bars = ax.bar(etiquetas, valores, color=colores)  # dibujar barras con colores de CLASS_INFO
    ax.set_title(titulo)  # establecer título
    ax.set_xlabel("Habitat")  # etiquetar eje X
    ax.set_ylabel("Area (ha)")  # etiquetar eje Y en hectáreas
    ax.grid(True, alpha=0.3)  # activar rejilla ligera

    # asegurar un margen superior para que quepan las etiquetas por encima de las barras
    max_val = max(valores) if valores else 0  # calcular máximo de la serie
    ax.set_ylim(0, max_val * 1.15 if max_val else 1)  # fijar rango Y con margen superior

    # añadir etiquetas numéricas (2 decimales) encima de cada barra, en negrita y tamaño mayor
    for b, v in zip(bars, valores):  # iterar barras y valores
        ax.text(  # escribir texto sobre la barra
            b.get_x() + b.get_width() / 2.0,  # posicionar texto en el centro de la barra
            b.get_height(),  # posicionar texto justo encima de la barra
            f"{v:.2f}",  # formatear el valor con 2 decimales
            ha="center", va="bottom",  # alinear horizontal y verticalmente
            fontweight="bold", fontsize=12  # aplicar negrita y tamaño de fuente mayor
        )

    fig.tight_layout()  # ajustar márgenes
    buf = io.BytesIO()  # crear buffer en memoria
    fig.savefig(buf, format="png")  # guardar figura como PNG en el buffer
    plt.close(fig)  # cerrar figura para liberar memoria
    buf.seek(0)  # reposicionar al inicio del buffer
    return buf  # devolver buffer listo para enviar

def _accretion_volume_by_class(class_tif, acc_tif):
    with rasterio.open(class_tif) as cls:
        class_arr = cls.read(1)

    with rasterio.open(acc_tif) as acc:
        acc_arr = acc.read(1, masked=True)
        resx, resy = acc.res
        pixel_area_m2 = abs(resx * resy)

    # Verificación rápida de alineación
    if class_arr.shape != acc_arr.shape:
        raise ValueError("Class raster and accretion raster are not aligned.")

    # Rellenar NoData con 0 para que no aporten volumen
    acc_filled = np.ma.filled(acc_arr, 0.0)

    # Σ(espesor) por clase con bincount (clases 0..3)
    sums = np.bincount(class_arr.ravel(), weights=acc_filled.ravel(), minlength=4)

    etiquetas, valores = [], []
    for v in sorted(CLASS_INFO.keys()):
        vol_m3 = float(sums[v] * pixel_area_m2)
        if abs(vol_m3) > 1e-9:
            etiquetas.append(CLASS_INFO[v][0])
            valores.append(vol_m3)
    return etiquetas, valores

def _png_grafico_accretion(titulo, etiquetas, valores):
    colores = [LABEL_TO_COLOR[e] for e in etiquetas]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    bars = ax.bar(etiquetas, valores, color=colores)
    ax.set_title(titulo)
    ax.set_xlabel("Habitat")
    ax.set_ylabel("Accretion volume (m³)")
    ax.grid(True, alpha=0.3)
    ymax = max(valores) if valores else 0
    ax.set_ylim(0, ymax*1.15 if ymax else 1)
    for b, v in zip(bars, valores):
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.2f}",
                ha="center", va="bottom", fontweight="bold", fontsize=12)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


# Registrar callbacks del tab de saltmarsh

def register_tab_callbacks(app: dash.Dash):  # definir función pública para registrar callbacks
    @app.callback(  # definir callback para renderizar el contenido de la pestaña
        Output("tab-content", "children"),  # salida: hijos del contenedor de pestaña
        Input("tabs", "value")  # entrada: valor de la pestaña seleccionada
    )
    def render_tab(tab):  # definir función de renderizado
        if tab == "tab-saltmarsh":  # comprobar si la pestaña activa es saltmarsh
            return html.Div([  # construir la UI de la pestaña de saltmarsh
                html.Div(  # contenedor para controles de selección
                    style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},  # aplicar estilos flex
                    children=[  # hijos del contenedor
                        dcc.Dropdown(  # desplegable del área de estudio
                            id="study-area-dropdown",  # establecer id del control
                            options=[  # definir opciones disponibles
                                {"label":"Urdaibai Estuary","value":"Urdaibai_Estuary"},  # opción Urdaibai
                                {"label":"Bay of Santander","value":"Bay_of_Santander"},  # opción Santander
                                {"label":"Cadiz Bay","value":"Cadiz_Bay"},  # opción Cádiz
                            ],
                            placeholder="Select Study Area",  # mostrar texto de ayuda
                            className='dropdown-text'  # aplicar clase CSS
                        ),
                        dcc.Dropdown(  # desplegable de escenario
                            id="scenario-dropdown",  # id del escenario
                            options=[  # opciones de escenarios
                                {"label":"Regional RCP4.5","value":"regional_rcp45"},  # opción RCP4.5 regional
                                {"label":"Regional RCP8.5","value":"regional_rcp85"},  # opción RCP8.5 regional
                                {"label":"Global RCP4.5","value":"global_rcp45"},  # opción RCP4.5 global
                            ],
                            placeholder="Select Scenario",  # texto de ayuda
                            className="dropdown-text"  # clase CSS
                        ),
                        dcc.Dropdown(  # desplegable del año
                            id="year-dropdown",  # id del año
                            options=[],  # iniciar sin opciones hasta elegir área
                            placeholder="Year",  # texto de ayuda
                            className="dropdown-text",  # clase CSS
                            disabled=True  # deshabilitar hasta elegir área
                        ),
                        html.Div(  # contenedor de botones Run/Reset
                            style={'display':'flex','gap':'10px','alignItems':'center'},  # estilo flex de fila
                            children=[  # hijos del contenedor de botones
                                html.Button(  # botón de ejecución
                                    html.Span("Run"),  # texto del botón
                                    id="run-button",  # id del botón
                                    n_clicks=0,  # contador de clicks inicial
                                    disabled=True,  # deshabilitar hasta seleccionar todo
                                    className='dropdown-text',  # clase CSS
                                    style={'width':'100px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}  # estilos
                                ),
                                html.Button(  # botón de reinicio
                                    html.Span("Restart"),  # texto del botón
                                    id="reset-button",  # id del botón
                                    n_clicks=0,  # contador de clicks inicial
                                    className= 'dropdown-text',  # clase CSS
                                    disabled=True,  # deshabilitado al inicio
                                    style={'display':'none','width':'100px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}  # estilos
                                )
                            ]
                        )
                    ]
                ),
                dcc.Loading(  # envoltorio de loading para contenidos que tardan
                    children = [  # elementos que muestran spinner mientras cargan
                            html.Div(id="saltmarsh-chart", style={'marginTop':'20px'}),  # contenedor para gráficas
                            html.Div(  # barra de botones inferior
                                id='button-bar',  # id del contenedor de botones
                                style= {'display':'flex','justifyContent':'center','alignItems':'center', 'verticalAlign': 'middle', 'gap': '12px'},  # estilos de alineación
                                children=[  # hijos de la barra
                                    html.Button([  # botón de información de hábitat
                                        html.Span([  # contenedor del contenido del botón
                                            html.Img(src='/assets/logos/info.png', style={'width': '20px', 'height': '20px'}),  # icono informativo
                                            html.Span("Habitat and accretion info")  # texto del botón
                                        ])
                                    ], id='info-button', style=BTN_STYLE, hidden=True, n_clicks=0),
                                    html.Div([  # contenedor de descarga de resultados
                                        html.Button([
                                            html.Img(src='/assets/logos/download.png', style={'width': '20px', 'height': '20px'}), html.Span("Download results")], id='marsh-results', hidden=True, n_clicks=0, style=BTN_STYLE),  # botón con icono de descarga
                                        dcc.Download(id='saltmarsh-download')  # componente de descarga de Dash
                                    ])
                                ]
                            ),
                    ], id="loading", type="circle", # configurar spinner circular
                ),

                dbc.Modal(  # modal de información de hábitats
                    [  # contenido del modal
                        dbc.ModalHeader(dbc.ModalTitle("Habitat & accretion information")),  # cabecera del modal
                        dbc.ModalBody(  # cuerpo del modal con lista de descripciones
                            html.Ul([
                                html.Li([html.B("Mudflat: "), html.I("Mudflats")," represent an important part of coastal wetlands, which, like marshes, provide a wide range of ecosystem services such as coastal defence and carbon sequestration."]),  # info Mudflat
                                html.Li([html.B("Saltmarsh: "), html.I("Saltmarshes"), " are coastal wetlands characterized by its low-lying, flat, and poorly drained soil that is regularly or occasionally flooded by salty or brackish water. Like Mudflats, saltmarshes provide a wide range of ecosystem services such as coastal defence, carbon sequestration and food provisioning."]),  # info Saltmarsh
                                html.Li([html.B("Upland Areas: "), html.I("Upland Areas"), " represent non-flooded areas where marshes can migrate during sea level rise conditions."]),  # info Upland
                                html.Li([html.B("Channel: "), html.I("Channels"), " are key features of wetlands that control fundamental dynamics like sediment availability, nutrient circulation and hydrodynamics."]),  # info Channel
                                html.Li([html.B("Accretion: "), html.I("Accretion"), " is the process where the elevation of a saltmarsh surface increases over time, either by the accumulation of mineral sediments (like silt and clay) or by the buildup of organic matter from decaying plant material. Through ", html.I("accretion"), ", saltmarshes sequester carbon from both accumulation of mineral sediments and organic matter from decaying plant material. "]) # info Accretion
                            ])
                        ),
                        dbc.ModalFooter(  # pie del modal con botón de cierre
                            dbc.Button("Close", id="info-close", className="ml-auto", n_clicks=0)  # botón cerrar
                        )
                    ],
                    id="info-modal",  # id del modal
                    is_open=False,    # iniciar cerrado
                    size="lg",  # tamaño grande
                    centered=True,  # centrar en pantalla
                    backdrop=True  # activar backdrop
                )

            ], style={'padding':'20px'})  # aplicar padding general
        else:  # si la pestaña no es saltmarsh
            return html.Div(f"Contenido de {tab}")  # devolver un marcador simple

    @app.callback(  # callback para poblar años según área
        Output("year-dropdown","options"),  # salida: opciones del desplegable de año
        Output("year-dropdown","disabled"),  # salida: habilitar/deshabilitar control
        Input("study-area-dropdown","value")  # entrada: valor de área seleccionada
    )
    def update_year_options(area):  # definir función de actualización de años
        if area=="Urdaibai_Estuary": years=[2017,2067,2117]  # asignar años para Urdaibai
        elif area=="Bay_of_Santander": years=[2012,2062,2112]  # asignar años para Santander
        elif area=="Cadiz_Bay": years=[2023,2073,2123]  # asignar años para Cádiz
        else: return [], True  # si no hay área, no hay opciones y se deshabilita
        return ([{"label":str(y),"value":y} for y in years], False)  # devolver opciones y habilitar

    @app.callback(  # callback para centrar y hacer zoom según área
        Output("map", "viewport"),  # salida: viewport del mapa
        Input("study-area-dropdown", "value")  # entrada: cambio de área
    )
    def center_and_zoom(area):  # definir función de centrado de mapa
        if not area:  # si no hay área seleccionada
            raise PreventUpdate  # no actualizar
        mapping = {  # definir centros y zoom por área
            "Urdaibai_Estuary":   ([43.364580815052316, -2.67957208131426804], 14),  # viewport Urdaibai
            "Bay_of_Santander":   ([43.43984351219931,  -3.7526739449807447], 15),  # viewport Santander
            "Cadiz_Bay":          ([36.520874060327226, -6.203490800462997],  15)   # viewport Cádiz
        }
        center, zoom = mapping[area]  # extraer centro y zoom
        return {"center": center, "zoom": zoom}  # devolver objeto viewport

    @app.callback(  # callback para activar el botón Run cuando todo está seleccionado
        Output("run-button","disabled", allow_duplicate=True),  # salida: estado disabled del botón Run
        Input("study-area-dropdown","value"),  # entrada: valor de área
        Input("scenario-dropdown","value"),  # entrada: valor de escenario
        Input("year-dropdown","value"),  # entrada: valor de año
        prevent_initial_call=True  # evitar ejecución inicial
    )
    def toggle_run(area,scen,year):  # definir función de conmutación del botón
        return not (area and scen and year)  # habilitar sólo si hay valores en los tres controles

    @app.callback(  # callback para pintar el ráster en el mapa y preparar UI de resultados
        Output("raster-layer","children", allow_duplicate=True),  # salida: hijos de la capa ráster
        Output("reset-button", "disabled"),  # salida: estado disabled del botón reset
        Output("study-area-dropdown", "disabled", allow_duplicate=True),  # salida: deshabilitar selección de área
        Output("scenario-dropdown", "disabled", allow_duplicate=True),  # salida: deshabilitar selección de escenario
        Output("year-dropdown", "disabled", allow_duplicate=True),  # salida: deshabilitar selección de año
        Output("run-button", "disabled"),  # salida: deshabilitar botón Run
        Output('marsh-results', 'hidden'),  # salida: mostrar botón de resultados
        Input("run-button","n_clicks"),  # entrada: clicks en Run
        State("study-area-dropdown","value"),  # estado: área
        State("scenario-dropdown","value"),  # estado: escenario
        State("year-dropdown","value"),  # estado: año
        prevent_initial_call=True  # evitar ejecución al cargar
    )
    def update_map(n,area,scen,year):  # definir función de actualización del mapa
        if not (n and area and scen and year):  # validar entradas
            return [], True, False, False, False, True, True  # devolver estado seguro si falta algo
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
        return [overlay, False, True, True, True, True, False]  # activar UI de resultados y bloquear selecciones

    @app.callback(  # callback de reseteo de selección y limpieza de UI
        Output("study-area-dropdown", "value", allow_duplicate=True),  # salida: valor del área
        Output("study-area-dropdown", "disabled", allow_duplicate=True),  # salida: estado disabled del área
        Output("scenario-dropdown", "value", allow_duplicate=True),  # salida: valor del escenario
        Output("scenario-dropdown", "disabled", allow_duplicate=True),  # salida: estado disabled del escenario
        Output("year-dropdown", "value", allow_duplicate=True),  # salida: valor del año
        Output("year-dropdown", "disabled", allow_duplicate=True),  # salida: estado disabled del año
        Output("raster-layer", "children", allow_duplicate=True),  # salida: limpiar capa ráster
        Output("saltmarsh-chart", "children", allow_duplicate=True),  # salida: limpiar gráficos
        Output('info-button', 'hidden', allow_duplicate=True),  # salida: ocultar botón info
        Output('marsh-results', 'hidden', allow_duplicate=True),
        Input("reset-button", "n_clicks"),  # entrada: clicks del reset
        prevent_initial_call = True  # evitar ejecución inicial
    )
    def reset(n):  # definir función de reset
        if n:  # si hay click
            return [None, False, None, False, None, True, [], [], True,  True] # limpiar valores, re-habilitar selects y deshabilitar año sin área
        raise PreventUpdate  # evitar actualización si no hay click
    

    @app.callback(  # callback para construir las gráficas (con pestañas internas) y mostrar botón Info
        Output("saltmarsh-chart", "children"),  # salida: contenido del contenedor de gráficas
        Output('info-button', "hidden"),  # salida: visibilidad del botón de info
        Input("run-button", "n_clicks"),  # entrada: clicks en Run
        State("study-area-dropdown", "value"),  # estado: área
        State("scenario-dropdown", "value"),  # estado: escenario
        State("year-dropdown", "value"),  # estado: año
        prevent_initial_call=True  # evitar ejecución al cargar
    )
    def update_saltmarsh_chart(n, area, scen, year):  # definir función para actualizar gráficas
        if not (n and area and scen and year):  # validar entradas
            raise PreventUpdate  # no actualizar si falta algo
        tif_dir = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)  # construir ruta a datos
        tif_path = glob.glob(os.path.join(tif_dir, f"*{year}*.tif"))  # buscar TIF de clases
        if not tif_path:  # comprobar existencia
            raise PreventUpdate  # abortar si no hay TIF
        tif_path = tif_path[0]  # tomar primer TIF

        etiquetas, areas_ha, colores = _areas_por_habitat(tif_path)  # calcular áreas por hábitat

        # Gráfica de áreas por hábitat con colores fijos y orden categórico estable
        fig_areas = px.bar(  # crear gráfica interactiva de áreas con Plotly
            x=etiquetas,  # establecer eje X (etiquetas)
            y=areas_ha,  # establecer eje Y (hectáreas)
            title="<b>Habitat Areas (ha)</b>",  # título de la gráfica
            color=etiquetas,  # colorear por etiqueta
            color_discrete_map=LABEL_TO_COLOR  # fijar colores por etiqueta
        )

        fig_areas.update_traces(texttemplate='<b>%{y:.2f}</b>', textposition='outside', cliponaxis=False)
        fig_areas.update_layout(showlegend=False, xaxis_title = "<b>Habitat</b>", yaxis_title = "<b>Area (ha)</b>", title_x = 0.5, title_font_family="Garamond", title_font_size = 25)  # ajustar layout y rango para que quepa el texto
        fig_areas.update_layout(uniformtext_minsize=10, uniformtext_mode='show')
        fig_areas.update_xaxes(categoryorder='array', categoryarray=CATEGORY_ORDER)  # forzar orden de categorías

        # Intentar localizar y representar ráster de acreción (media por hábitat)
        acc_tif = _acc_tif_from_class_tif(tif_path)
        if acc_tif:  # si existe ráster de acreción
            etiquetas_acc, valores_acc = _accretion_volume_by_class(tif_path, acc_tif)
            if not valores_acc:
                acc_tab_child = html.Div(
                    "No non-zero accumulated accretion found for this scenario.",
                    style={"color": "#555", "fontStyle": "italic"}
                )
            else:
                fig_acc = px.bar(
                    x=etiquetas_acc, y=valores_acc,
                    title="<b>Accumulated Accretion (m³) by habitat</b>",
                    color=etiquetas_acc, color_discrete_map=LABEL_TO_COLOR
                )
                y2_max = max(valores_acc)
                fig_acc.update_traces(
                    texttemplate='<b>%{y:.2f}</b>',
                    textposition='outside',
                    textfont_size=14,
                    cliponaxis=False
                )
                fig_acc.update_layout(
                    showlegend=False,
                    xaxis_title="<b>Habitat</b>",
                    yaxis_title="<b>Accretion volume (m³)</b>",
                    title_x=0.5,
                    title_font_family="Garamond",
                    title_font_size=25,
                    yaxis_range=[0, y2_max*1.2 if y2_max else 1],
                    uniformtext_minsize=10,
                    uniformtext_mode='show'
                )
                fig_acc.update_xaxes(categoryorder='array', categoryarray=CATEGORY_ORDER)
                acc_tab_child = dcc.Graph(
                    figure=fig_acc,
                    config={"modeBarButtonsToRemove": ["zoom2d","pan2d","zoomIn2d","zoomOut2d","lasso2d","resetScale2d"]}
                )

        else:  # si no se encontró ráster de acreción
            acc_tab_child = html.Div("No accretion raster found in this scenario folder.", style={"color":"#555", "fontStyle":"italic"})  # mostrar mensaje informativo
        charts = dcc.Tabs(  # crear pestañas internas para alternar resultados
            id="saltmarsh-inner-tabs",  # id del control de pestañas internas
            value="areas",  # seleccionar por defecto la pestaña de áreas
            children=[  # hijos: pestañas
                dcc.Tab(label='Habitat Areas', value='areas', children=[  # pestaña de áreas
                    dcc.Graph(figure=fig_areas, config={"modeBarButtonsToRemove": ["zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "lasso2d", "resetScale2d"]})  # incluir gráfica de áreas
                ]),
                dcc.Tab(label='Accumulated Accretion', value='accretion', children=[  # pestaña de acreción
                    acc_tab_child  # incluir gráfica o texto según disponibilidad
                ])
            ]
        )
        return [charts, False]  # devolver pestañas y mostrar botón de info

    @app.callback(  # callback para generar un ZIP con el PNG del gráfico y el TIF usado
        Output('saltmarsh-download', 'data'),  # salida: datos de descarga (ZIP)
        Input('marsh-results', 'n_clicks'),  # entrada: clicks en el botón Results
        State("study-area-dropdown", "value"),  # estado: área
        State("scenario-dropdown", "value"),  # estado: escenario
        State("year-dropdown", "value"),  # estado: año
        prevent_initial_call=True  # evitar ejecución al cargar
    )
    def download_results(n, area, scen, year):  # definir función de descarga
        if not (n and area and scen and year):  # validar entradas
            raise PreventUpdate  # no hacer nada si faltan parámetros
        tif_path = _find_class_tif(area, scen, year)  # localizar el TIF de clases
        if not tif_path:  # comprobar existencia del TIF
            raise PreventUpdate  # no descargar si no hay TIF

        etiquetas, areas_ha, colores = _areas_por_habitat(tif_path)  # calcular áreas por hábitat
        titulo = f"Habitat Areas — {area} / {scen} / {year}"  # construir título del gráfico PNG
        png_buf = _png_grafico_areas(titulo, etiquetas, areas_ha, colores)  # generar PNG del gráfico en memoria




        # 1) localizar el TIF de acreción emparejado
        acc_tif = _acc_tif_from_class_tif(tif_path)

        # 2) si existe, calcular volúmenes y crear PNG
        if acc_tif:
            try:
                etiquetas_acc, valores_acc = _accretion_volume_by_class(tif_path, acc_tif)
                if valores_acc:  # sólo si hay volúmenes > 0
                    titulo_acc = f"Accumulated Accretion — {area} / {scen} / {year}"
                    acc_png_buf = _png_grafico_accretion(titulo_acc, etiquetas_acc, valores_acc)
            except Exception as e:
                etiquetas_acc, valores_acc, acc_png_buf = [], [], None
        else:
            etiquetas_acc, valores_acc, acc_png_buf = [], [], None

        zip_buf = io.BytesIO()
        # 3) escribir en el ZIP
        with ZipFile(zip_buf, 'w') as zf:
            # ya tenías:
            zf.writestr(f"habitat_areas_{area}_{scen}_{year}.png", png_buf.getvalue())
            zf.write(tif_path, arcname=os.path.basename(tif_path))

            # nuevo: PNG de accretion y TIF de accretion (si existe)
            if acc_png_buf:
                zf.writestr(f"accumulated_accretion_{area}_{scen}_{year}.png", acc_png_buf.getvalue())
            if acc_tif and os.path.exists(acc_tif):
                zf.write(acc_tif, arcname=os.path.basename(acc_tif))
        zip_buf.seek(0)
        zip_bytes = zip_buf.getvalue()
        filename = f"saltmarsh_results_{area}_{scen}_{year}.zip"
        return dcc.send_bytes(lambda f: f.write(zip_bytes), filename=filename)


    @app.callback(  # callback para mostrar/ocultar el modal de información
        Output("info-modal", "is_open"),  # salida: estado abierto del modal
        Input("info-button", "n_clicks"),  # entrada: clicks en botón de info
        Input("info-close",  "n_clicks"),  # entrada: clicks en botón de cierre
        State("info-modal",  "is_open"),  # estado: estado actual del modal
        prevent_initial_call=True  # evitar ejecución al cargar
    )
    def toggle_info_modal(open_clicks, close_clicks, is_open):  # definir función de toggle del modal
        ctx = callback_context  # acceder al contexto del callback
        if not ctx.triggered:  # si no hay disparador
            raise PreventUpdate  # no actualizar
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]  # identificar el id del disparador
        if trigger in ["info-button", "info-close"]:  # si se pulsó info o cerrar
            return not is_open  # alternar estado del modal
        return is_open  # mantener estado si el disparador no es reconocido
