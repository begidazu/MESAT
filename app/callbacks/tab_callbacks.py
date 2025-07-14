# import os, glob
# import dash_leaflet as dl
# import rasterio
# from rasterio.vrt import WarpedVRT
# from rasterio.enums import Resampling
# from rasterio.transform import rowcol



# from dash import Input, Output, State, html, dcc
# import dash

# def register_tab_callbacks(app: dash.Dash):
#     @app.callback(
#         Output("tab-content", "children"),
#         Input("tabs", "value")
#     )
#     def render_tab(tab):
#         if tab == "tab-saltmarsh":
#             return html.Div([
#             # Contenedor columnar para dropdowns
#                 html.Div(
#                     style={
#                         'display': 'flex',
#                         'flexDirection': 'column',
#                         'gap': '15px',            # separa verticalmente
#                         'width': '100%'
#                     },
#                     children=[
#                         dcc.Dropdown(
#                             id="study-area-dropdown",
#                             options=[
#                                 {"label": "Urdaibai Estuary",  "value": "Urdaibai_Estuary"},
#                                 {"label": "Bay of Santander",  "value": "Bay_of_Santander"},
#                                 {"label": "Cadiz Bay",         "value": "Cadiz_Bay"},
#                             ],
#                             placeholder="Select Study Area",
#                             style={'fontSize': '18px'}
#                         ),
#                         dcc.Dropdown(
#                             id="scenario-dropdown",
#                             options=[
#                                 {"label": "Regional RCP4.5", "value": "regional_rcp45"},
#                                 {"label": "Regional RCP8.5", "value": "regional_rcp85"},
#                                 {"label": "Global RCP4.5",   "value": "global_rcp45"},
#                             ],
#                             placeholder="Select Scenario",
#                             style={'fontSize': '18px'}
#                         ),
#                         dcc.Dropdown(
#                             id="year-dropdown",
#                             options=[],
#                             placeholder="Year",
#                             disabled=True,
#                             style={'fontSize': '18px'}
#                         ),
#                         # Botón grande, con flecha centrada
#                         html.Button(
#                             html.Span("▶", style={'fontSize': '24px', 'lineHeight': '24px'}),
#                             id="run-button",
#                             n_clicks=0,
#                             disabled = True,
#                             style={
#                                 'alignSelf': 'flex-end',   # lo mueve a la derecha
#                                 'width': '60px',
#                                 'height': '60px',
#                                 'borderRadius': '50%',
#                                 'fontSize': '24px',
#                                 'display': 'flex',
#                                 'justifyContent': 'center',
#                                 'alignItems': 'center',
#                                 'marginTop': '10px'
#                             }
#                         ),
#                         html.Button(
#                             "⟳",
#                             id="reset-button",
#                             n_clicks = 0,
#                             style={'display':'none','width':'60px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}
#                         )
#                     ]
#                 ),
#             # Luego tu gráfico/tabla…
#             html.Div(id="saltmarsh-chart", style={'marginTop': '30px'})
#         ], style={'padding': '20px'})
#         else:
#             # Para otras pestañas, pones tu contenido actual
#             return html.Div(f"Contenido de {tab}")
#     @app.callback(
#             Output("year-dropdown", "options"),
#             Output("year-dropdown", "disabled"),
#             Input("study-area-dropdown", "value")
#         )
#     def update_year_options(area):
#         if area == "Urdaibai_Estuary":
#             years = [2017, 2067, 2117]
#         elif area == "Bay_of_Santander":
#             years = [2012, 2062, 2112]
#         elif area == "Cadiz_Bay":
#             years = [2023, 2073, 2123]
#         else:
#             return [], True
#         opts = [{"label": str(y), "value": y} for y in years]
#         return opts, False
    
#     # ————————————————
#     # Habilitar Run solo si hay 3 selecciones
#     # ————————————————

#     @app.callback(
#         Output("run-button", "disabled"),
#         Input("study-area-dropdown", "value"),
#         Input("scenario-dropdown", "value"),
#         Input("year-dropdown", "value"),
#     )
#     def toggle_run_button(area, scenario, year):
#         # Si cualquiera no está seleccionado, botón deshabilitado
#         if not (area and scenario and year):
#             return True
#         return False
    
#     # ————————————————
#     # Al pulsar Run: cargar TIFF y hacer zoom
#     # ————————————————
#     @app.callback(
#         Output("map", "children"),
#         Output("map", "bounds"),
#         Input("run-button", "n_clicks"),
#         State("study-area-dropdown", "value"),
#         State("scenario-dropdown",    "value"),
#         State("year-dropdown",        "value"),
#         State("map",                  "children")
#     )
#     def update_map(n,area,scen,year,bounds):
#         if not (n and area and scen and year): return [], bounds
#         tif_dir=os.path.join(os.getcwd(),"results","saltmarshes",area,scen)
#         m=glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))[0]
#         with rasterio.open(m) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:
#             data=vrt.read(1,masked=True)
#             # maskear nodata=0
#             import numpy as np; data=np.ma.masked_where(data.data==0,data)
#             b=vrt.bounds; w,h=vrt.width,vrt.height
#         from matplotlib.colors import ListedColormap,BoundaryNorm
#         cmap=ListedColormap(["#8B4513","#006400","#2F4F4F","#ADD8E6"])
#         norm=BoundaryNorm([0,1,2,3,4],4)
#         from io import BytesIO; import matplotlib.pyplot as plt
#         fig=plt.figure(frameon=False); fig.set_size_inches(w/100,h/100)
#         ax=fig.add_axes([0,0,1,1])
#         im=ax.imshow(data,cmap=cmap,norm=norm,extent=(b.left,b.right,b.bottom,b.top),interpolation="nearest",origin="upper")
#         ax.axis("off")
#         buf=BytesIO(); fig.savefig(buf,dpi=100,transparent=True,pad_inches=0); plt.close(fig); buf.seek(0)
#         url=f"/raster/{area}/{scen}/{year}.png"
#         overlay=dl.ImageOverlay(url=url,bounds=[[b.bottom,b.left],[b.top,b.right]],opacity=0.7)
#         return [overlay], [[b.bottom,b.left],[b.top,b.right]]
#     # def update_map(n_clicks, area, scenario, year, existing_layers):
        
#     #     # Partimos de las capas existentes (TileLayer + controles)
#     #     layers = existing_layers[:] if existing_layers else [dl.TileLayer()]

#     #     # Sólo actuamos tras pulsar y con los 3 valores seleccionados
#     #     if not (n_clicks and area and scenario and year):
#     #         return layers, None

#     #     # Convertir label → carpeta
#     #     folder_area = area

#     #     # Construir URL pública y ruta local del TIF
#     #     img_url = f"/raster/{area}/{scenario}/{year}.png"
#     #     print("DEBUG ➔ img_url =", img_url)  
#     #     dirpath = os.path.join(os.getcwd(), "results", "saltmarshes", folder_area, scenario)
#     #     matches = glob.glob(os.path.join(dirpath, f"*{year}*.tif"))
#     #     if not matches:
#     #         return layers, None
#     #     tif_path = matches[0]

#     #     print("DEBUG ➔ looking in dir:", dirpath)
#     #     print("DEBUG ➔ glob pattern:", f"*{year}*.tif", "matches:", matches)
#     #     print("DEBUG ➔ using tif_path:", tif_path)

#     #     # Obtener bounds reproyectados
#     #     with rasterio.open(tif_path) as src, WarpedVRT(src, crs="EPSG:4326") as vrt:
#     #         b = vrt.bounds
#     #         bounds = [[b.bottom, b.left], [b.top, b.right]]

#     #     # Añadir la capa ráster
#     #     layers.append(
#     #         dl.ImageOverlay(
#     #             url=img_url,
#     #             bounds=bounds,
#     #             interactive=False,
#     #             zIndex=1000
#     #         )
#     #     )

#     #     # Devolvemos layers + nuevos bounds para hacer zoom
#     #     return layers, bounds
    
#     @app.callback(
#         Output("popup-layer","children"),
#         Input("map","click_lat_lng"),
#         State("popup-layer","children"),
#         State("study-area-dropdown","value"),
#         State("scenario-dropdown","value"),
#         State("year-dropdown","value")
#     )
#     def display_popup(click, pops,area,scen,year):
#         if not click or not (area and scen and year): return pops
#         lat,lon=click
#         tif_dir=os.path.join(os.getcwd(),"results","saltmarshes",area,scen)
#         tif=glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))[0]
#         with rasterio.open(tif) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:
#             row,col=rowcol(vrt.transform,lon,lat)
#             val=int(vrt.read(1,masked=False)[row,col])
#         names={0:"Mudflat",1:"Saltmarsh",2:"Upland Areas",3:"Channel"}
#         marker=dl.Marker(position=(lat,lon),children=dl.Popup(names.get(val,f"Val:{val}")))
#         return pops+[marker]

# # Luego, en el create_app():
# # from .callbacks.tab_callbacks import register_tab_callbacks
# # register_tab_callbacks(app)

import os, glob
import dash_leaflet as dl
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import rowcol
from dash import Input, Output, State, html, dcc
import dash

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
                                "⟳",
                                id="reset-button",
                                n_clicks=0,
                                style={'display':'none','width':'60px','height':'60px','borderRadius':'50%','display':'flex','justifyContent':'center','alignItems':'center'}
                            )
                        ])
                    ]
                ),
                html.Div(id="saltmarsh-chart", style={'marginTop':'30px'})
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

    @app.callback(
        Output("run-button","disabled"),
        Input("study-area-dropdown","value"),
        Input("scenario-dropdown","value"),
        Input("year-dropdown","value")
    )
    def toggle_run(area,scen,year):
        return not (area and scen and year)

    @app.callback(
        Output("raster-layer","children"),
        Output("map","bounds"),
        Input("run-button","n_clicks"),
        State("study-area-dropdown","value"),
        State("scenario-dropdown","value"),
        State("year-dropdown","value"),
        State("map","bounds")
    )
    def update_map(n,area,scen,year,bounds):
        if not (n and area and scen and year): return [], bounds
        tif_dir=os.path.join(os.getcwd(),"results","saltmarshes",area,scen)
        m=glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))[0]
        with rasterio.open(m) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:
            data=vrt.read(1,masked=True)
            # maskear nodata=0
            import numpy as np; data=np.ma.masked_where(data.data==0,data)
            b=vrt.bounds; w,h=vrt.width,vrt.height
        from matplotlib.colors import ListedColormap,BoundaryNorm
        cmap=ListedColormap(["#8B4513","#006400","#BBC0C2","#34C3F3"])
        norm=BoundaryNorm([0,1,2,3,4],4)
        from io import BytesIO; import matplotlib.pyplot as plt
        fig=plt.figure(frameon=False); fig.set_size_inches(w/100,h/100)
        ax=fig.add_axes([0,0,1,1])
        im=ax.imshow(data,cmap=cmap,norm=norm,extent=(b.left,b.right,b.bottom,b.top),interpolation="nearest",origin="upper")
        ax.axis("off")
        buf=BytesIO(); fig.savefig(buf,dpi=100,transparent=True,pad_inches=0); plt.close(fig); buf.seek(0)
        url=f"/raster/{area}/{scen}/{year}.png"
        overlay=dl.ImageOverlay(url=url,bounds=[[b.bottom,b.left],[b.top,b.right]],opacity=1)
        return [overlay], [[b.bottom,b.left],[b.top,b.right]]

    @app.callback(
        Output("popup-layer","children"),
        Input("map","click_lat_lng"),
        State("popup-layer","children"),
        State("study-area-dropdown","value"),
        State("scenario-dropdown","value"),
        State("year-dropdown","value")
    )
    def display_popup(click, pops,area,scen,year):
        if not click or not (area and scen and year): return pops
        lat,lon=click
        tif_dir=os.path.join(os.getcwd(),"results","saltmarshes",area,scen)
        tif=glob.glob(os.path.join(tif_dir,f"*{year}*.tif"))[0]
        with rasterio.open(tif) as src, WarpedVRT(src,crs="EPSG:4326",resampling=Resampling.nearest) as vrt:
            row,col=rowcol(vrt.transform,lon,lat)
            val=int(vrt.read(1,masked=False)[row,col])
        names={0:"Mudflat",1:"Saltmarsh",2:"Upland Areas",3:"Channel"}
        marker=dl.Marker(position=(lat,lon),children=dl.Popup(names.get(val,f"Val:{val}")))
        return pops+[marker]
