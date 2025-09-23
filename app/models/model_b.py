# app/models/model_b.py

import geopandas as gpd
from pyobis import occurrences
from shapely.geometry import box, Point, Polygon
from shapely.wkt import dumps as wkt_dumps


def run():
    # Lógica de Model B
    return {"message": "Resultado de Model B"}

# aoi = gpd.read_file(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.shp")
# aoi.to_parquet(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.parquet")

# def get_obis_occurrences(specie: str, wkt_geom: str, start_date: str, end_date: str) -> gpd.GeoDataFrame:
#         """
#         Downloads species occurrence data in the area of interest during the selected timeframe in the EPSG:4326 coordinate system.

#         Params:
#             specie: specie name
#             wkt_geom:  a WKT string of the area of interest where we want to download the occurrence data
#             start_date: start date in %Y-%m-%d format
#             end_date:  end date in %Y-%m-%d format
        
#         Returns:
#         A gpd.GeoDataFrame with the occurrence points of the specie. From the points with same lat/long the function keeps the first point. 
#         """
#         occ_data = occurrences.search(
#             scientificname=specie,
#             geometry=wkt_geom,
#             startdate=start_date,
#             enddate=end_date
#         ).execute()

#         fil_occ_data = occ_data.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"], keep="first")
#         filtered_occ_data = fil_occ_data[["scientificName", "datasetID", "decimalLatitude", "decimalLongitude"]]

#         geometry = [Point(xy) for xy in zip(filtered_occ_data["decimalLongitude"], filtered_occ_data["decimalLatitude"])]
#         occ_gdf = gpd.GeoDataFrame(filtered_occ_data, geometry=geometry)
#         occ_gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)
#         return occ_gdf

# def wkt_from_first_geom(aoi_gdf_4326: gpd.GeoDataFrame, simplify_tol: float = 0.005) -> str:
#     """
#     Converts the area of interest geometries into a WKT string that will be used to download OBIS data
#     """
#     geom = aoi_gdf_4326.geometry.iloc[0]
#     geom_s = geom.simplify(simplify_tol, preserve_topology=True)
#     return wkt_dumps(geom_s, rounding_precision=6)

# aoi_4326 = gpd.read_parquet(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\BBT_Gulf_of_Biscay.parquet").to_crs("EPSG:4326")
# wkt_geom = wkt_from_first_geom(aoi_4326)

# data = get_obis_occurrences("Zostera noltii", wkt_geom, "2020-01-01", "2023-12-31")

# data.to_parquet(r"C:\Users\beñat.egidazu\Desktop\Tests\EVA_OBIS\Cantabria\Zostera_noltei.parquet")