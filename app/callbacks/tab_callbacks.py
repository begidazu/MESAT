import os, glob
import dash_leaflet as dl
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import rowcol
from dash import Input, Output, State, html, dcc
import dash
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from matplotlib.colors import ListedColormap,BoundaryNorm
import plotly.express as px
import numpy as np

def register_tab_callbacks(app: dash.Dash):
    @app.callback(
        Output("tab-content", "children"),
        Input("tabs", "value")
    )
    def render_tab(tab):
        if tab == "tab-saltmarsh":
            return html.Div([
                html.Div(
                    style={'display':'flex','flexDirection':'column','gap':'15px','width':'100%'},
                    children=[
                        dcc.Dropdown(
                            id="study-area-dropdown",
                            options=[
                                {"label":"Urdaibai Estuary","value":"Urdaibai_Estuary"},
                                {"label":"Bay of Santander","value":"Bay_of_Santander"},
                                {"label":"Cadiz Bay","value":"Cadiz_Bay"},
                            ],
                            placeholder="Select Study Area",
                            style={'fontSize':'18px'}
                        ),
                        dcc.Dropdown(
                            id="scenario-dropdown",
                            options=[
                                {"label":"Regional RCP4.5","value":"regional_rcp45"},
                                {"label":"Regional RCP8.5","value":"regional_rcp85"},
                                {"label":"Global RCP4.5","value":"global_rcp45"},
                            ],
                            placeholder="Select Scenario",
                            style={'fontSize':'18px'}
                        ),
                        dcc.Dropdown(
                            id="year-dropdown",
                            options=[],
                            placeholder="Year",
                            disabled=True,
                            style={'fontSize':'18px'}
                        ),
                        html.Div(style={'display':'flex','gap':'10px','alignItems':'center'}, children=[
                            html.Button(
                                html.Span("▶", style={'fontSize':'24px'}),
                                id="run-button",
                                n_clicks=0,
                                disabled=True,
                                style={'width':'60px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}
                            ),
                            html.Button(
                                html.Span("⟳", style={'fontSize':'24px'}),
                                id="reset-button",
                                n_clicks=0,
                                disabled=True,
                                style={'display':'none','width':'60px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}
                            )
                        ])
                    ]
                ),
                # dcc.Loading(
                #         html.Div(id="saltmarsh-chart", style={'marginTop':'20px'}), id="loading", type="circle"),
                #         html.Button([
                #             html.Span([
                #                 html.Img(src='/assets/logos/info.png', style={'width': '30px', 'height': '30px', 'margin-right': '5px'}),
                #                 html.Div("Get habitat info", style={'display': 'inline-block', 'verticalAlign': 'middle', 'font-size' : '14px', 'font-style' : 'italic'})   #'font-weight' : 'bold'
                #             ], style={'display':'flex','justifyContent':'center','alignItems':'center', 'verticalAlign': 'middle'})
                #         ], id='info-button', style={'padding': '10px', 'margin-top': '20px', 'border-radius' : '5px'}, hidden= True)

                dcc.Loading(
                    children = [
                            html.Div(id="saltmarsh-chart", style={'marginTop':'20px'}),
                            html.Button([
                                html.Span([
                                    html.Img(src='/assets/logos/info.png', style={'width': '30px', 'height': '30px', 'margin-right': '5px'}),
                                    html.Div("Get habitat info", style={'display': 'inline-block', 'verticalAlign': 'middle', 'font-size' : '14px', 'font-style' : 'italic'})   #'font-weight' : 'bold'
                                ], style={'display':'flex','justifyContent':'center','alignItems':'center', 'verticalAlign': 'middle'})
                        ], id='info-button', style={'padding': '10px', 'margin-top': '20px', 'border-radius' : '5px'}, hidden= True)

                    ], id="loading", type="circle")
                        
                        

                    
            ], style={'padding':'20px'})
        else:
            return html.Div(f"Contenido de {tab}")

    @app.callback(
        Output("year-dropdown","options"),
        Output("year-dropdown","disabled"),
        Input("study-area-dropdown","value")
    )
    def update_year_options(area):
        if area=="Urdaibai_Estuary": years=[2017,2067,2117]
        elif area=="Bay_of_Santander": years=[2012,2062,2112]
        elif area=="Cadiz_Bay": years=[2023,2073,2123]
        else: return [], True
        return ([{"label":str(y),"value":y} for y in years], False)
    
    # 3) Centrar y hacer zoom en el mapa al cambiar área de estudio con viewport
    @app.callback(
        Output("map", "viewport"),
        Input("study-area-dropdown", "value")
    )
    def center_and_zoom(area):
        if not area:
            raise PreventUpdate
        # Coordenadas y nivel de zoom dedicados para cada área
        mapping = {
            "Urdaibai_Estuary":   ([43.364580815052316, -2.67957208131426804], 14),
            "Bay_of_Santander":   ([43.43984351219931,  -3.7526739449807447], 15),
            "Cadiz_Bay":          ([36.520874060327226, -6.203490800462997],  15)
        }
        center, zoom = mapping[area]
        return {"center": center, "zoom": zoom}

    @app.callback(
        Output("run-button","disabled", allow_duplicate=True),
        Input("study-area-dropdown","value"),
        Input("scenario-dropdown","value"),
        Input("year-dropdown","value"),
        prevent_initial_call=True
    )
    def toggle_run(area,scen,year):
        return not (area and scen and year)

    @app.callback(
        Output("raster-layer","children", allow_duplicate=True),
        Output("reset-button", "disabled"),
        Output("study-area-dropdown", "disabled", allow_duplicate=True),
        Output("scenario-dropdown", "disabled", allow_duplicate=True),
        Output("year-dropdown", "disabled", allow_duplicate=True),
        Output("run-button", "disabled"),
        Input("run-button","n_clicks"),
        State("study-area-dropdown","value"),
        State("scenario-dropdown","value"),
        State("year-dropdown","value"),
        prevent_initial_call=True
    )
    def update_map(n,area,scen,year):
        
        if not (n and area and scen and year): return [] 
        tif_dir=os.path.join(os.getcwd(),"results","saltmarshes",area,scen)
        m=glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))[0]
        with rasterio.open(m) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:
            data=vrt.read(1,masked=True)
            # mask nodata=0
            import numpy as np; data=np.ma.masked_where(data.data==0,data)
            b=vrt.bounds; w,h=vrt.width,vrt.height
        cmap=ListedColormap(["#8B4513","#006400","#BBC0C2","#34C3F3"])
        norm=BoundaryNorm([0,1,2,3,4],4)
        from io import BytesIO; import matplotlib.pyplot as plt
        fig=plt.figure(frameon=False); fig.set_size_inches(w/100,h/100)
        ax=fig.add_axes([0,0,1,1])
        im=ax.imshow(data,cmap=cmap,norm=norm,extent=(b.left,b.right,b.bottom,b.top),interpolation="nearest",origin="upper")
        ax.axis("off")
        buf=BytesIO(); fig.savefig(buf,dpi=100,transparent=True,pad_inches=0); plt.close(fig); buf.seek(0)
        url=f"/raster/{area}/{scen}/{year}.png"
        overlay=dl.ImageOverlay(url=url,bounds=[[b.bottom, b.left], [b.top, b.right]],opacity=1)
        return [overlay, False, True, True, True, True]

    # This is not working right now
    #@app.callback(
    #    Output("popup-layer","children"),
    #    Input("map","click_lat_lng"),
    #    State("popup-layer","children"),
    #    State("study-area-dropdown","value"),
    #    State("scenario-dropdown","value"),
    #    State("year-dropdown","value")
    #)
    #def display_popup(click, pops,area,scen,year):
    #    if not click or not (area and scen and year): return pops
    #    lat,lon=click
    #    tif_dir=os.path.join(os.getcwd(),"results","saltmarshes",area,scen)
    #    tif=glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))[0]
    #    with rasterio.open(tif) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:
    #        row,col=rowcol(vrt.transform,lon,lat)
    #        val=int(vrt.read(1,masked=False)[row,col])
    #    names={0:"Mudflat",1:"Saltmarsh",2:"Upland Areas",3:"Channel"}
    #   marker=dl.Marker(position=(lat,lon),children=dl.Popup(names.get(val,f"Val:{val}")))
    #    return pops+[marker]
    
    # Here we will place the capabilities of the reset-button:
    @app.callback(
        Output("study-area-dropdown", "value", allow_duplicate=True),
        Output("study-area-dropdown", "disabled", allow_duplicate=True),
        Output("scenario-dropdown", "value", allow_duplicate=True),
        Output("scenario-dropdown", "disabled", allow_duplicate=True),
        Output("year-dropdown", "value", allow_duplicate=True),
        Output("year-dropdown", "disabled", allow_duplicate=True),
        Output("raster-layer", "children", allow_duplicate=True),
        Output("saltmarsh-chart", "children", allow_duplicate=True),
        Output('info-button', 'hidden', allow_duplicate=True),
        Input("reset-button", "n_clicks"),
        prevent_initial_call = True
    )
    def reset(n):
        if n:
            return ["Select Study Area", False, "Select Scenario", False, "Year", False, [], [], True]
    
    @app.callback(
        Output("saltmarsh-chart", "children"),         # dónde metemos la gráfica
        Output('info-button', "hidden"),
        Input("run-button", "n_clicks"),              # disparador: mismo que el mapa
        State("study-area-dropdown", "value"),        
        State("scenario-dropdown", "value"),
        State("year-dropdown", "value"),
        prevent_initial_call=True
    )
    def update_saltmarsh_chart(n, area, scen, year):
    # 1) Validar parámetros
        if not (n and area and scen and year):
            raise PreventUpdate

        # 2) Buscar fichero tif
        tif_dir = os.path.join(os.getcwd(), "results", "saltmarshes", area, scen)
        tif_path = glob.glob(os.path.join(tif_dir, f"*{year}*.tif"))[0]

        # 3) Leer datos de la banda
        with rasterio.open(tif_path) as src:
            arr = src.read(1)
            resolution = src.res
            pixel_area = resolution[0] * resolution[1]  # area of each pixel

        # 4) Contar valores únicos
        unique_vals, counts = np.unique(arr, return_counts=True)

        # 5) Mapear valores a nombres
        names = {0: "Mudflat", 1: "Saltmarsh", 2: "Upland Areas", 3: "Channel"}

        # 6) filtrar solo los valores que tenemos en 'names'
        datos = [(v, c) for v, c in zip(unique_vals, counts) if v in names]
        valores_filtrados = [v for v, _ in datos]                 
        cuentas_filtradas = [float(c * pixel_area / 10000) for _, c in datos]      # Converted to acres

        # 7) generar etiquetas en el mismo orden del filtrado
        etiquetas = [names[v] for v in valores_filtrados]        

        # 8) crear gráfica de barras con colores personalizados
        fig = px.bar(
            x=etiquetas,
            y=cuentas_filtradas,
            title="<b>Habitat Areas<b>",
            color=etiquetas,
            color_discrete_sequence=["#8B4513", "#006400", "#BBC0C2", "#34C3F3"]
        )
        fig.update_layout(showlegend=False, xaxis_title = "<b>Habitat<b>", yaxis_title = "<b>Area (ha)<b>", title_x = 0.5, title_font_family="Garamond", title_font_size = 25)

        # 9) Devolver componente gráfico
        return [dcc.Graph(figure=fig, config= {"modeBarButtonsToRemove": ["zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "lasso2d", "resetScale2d"]}), False] #https://github.com/plotly/plotly.js/blob/master/src/plot_api/plot_config.js, https://github.com/plotly/plotly.js/blob/master/src/components/modebar/buttons.js

    @app.callback(
        Output("loading", "display"),
        Input("run-button", "n_clicks")
    )
    def update_display(loading):
        return loading

    # Click on map pop-up event:
    # @app.callback(
    #     Output("popup", "children"),
    #     Output("popup", "position")
    # )
    # def popup(click):
    #     if click:
    #         return ["Hola", [40, -3]]