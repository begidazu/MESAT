# app/models/model_b.py

import geopandas as gpd
import pandas as pd
from pyobis import occurrences
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps


def run():
    # Lógica de Model B
    return {"message": "Resultado de Model B"}

# ane8 = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\stocks_simplify\ane8.shp")
# ane8.to_parquet(r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\ane8.parquet')

# ane9as = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\stocks_simplify\ane9aS.shp")
# ane9as.to_parquet(r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\ane9as.parquet')

# hom9a = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\stocks_simplify\hom9a.shp")
# hom9a.to_parquet(r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\hom9a.parquet')

# homnea = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\stocks_simplify\homnea.shp")
# homnea.to_parquet(r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\homnea.parquet')

# macnea = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\stocks_simplify\macnea.shp")
# macnea.to_parquet(r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\macnea.parquet')

# pil8c9a = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\MESIT_saltmarsh_impact\mesit2.shp")
# pil8c9a.to_parquet(r"C:\Users\beñat.egidazu\Desktop\Tests\MESIT_saltmarsh_impact\mesit2.parquet")

# table =  pd.read_excel(r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct\SPF_accounts_MESIT.xlsx")
# table.to_parquet(r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct\SPF_accounts_MESIT.parquet")

# import rasterio

# files = {
#     'ANE8': r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\presence_absence\taxonid=126426\method=ensemble\threshold=max_spec_sens\2000_2010.tif',
#     'MACNEA': r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\presence_absence\taxonid=127023\method=ensemble\threshold=max_spec_sens\2000_2010.tif',
#     'HOMNEA': r'C:\Users\beñat.egidazu\Documents\GitHub\PhD_Web_App\results\pelagic_fish_stocks\presence_absence\taxonid=126822\method=ensemble\threshold=max_spec_sens\2000_2010_0_25deg.tif',
#     # add others
# }

# for name, path in files.items():
#     with rasterio.open(path) as src:
#         print(f"{name}: CRS={src.crs}, bounds={src.bounds}, shape={src.shape}, dtype={src.dtypes}")