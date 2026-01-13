import geopandas as gpd
import joblib
import numpy as np
import os
from osgeo import gdal, ogr
from pyimpute import load_targets, impute
import pyproj
import rasterio
from rasterio.transform import from_origin

# ------------------------------------------------------------------------- INPUTS --------------------------------------------------------------------------------------------------
    # Output workspace:
out_folder = r"out_workspace"

    # Baseline habitat map (classier result):
saltmarsh_vegetation = rasterio.open(r"my_classifier\responses.tif")

# Baseline habitat map codes:
mudflat_code = 0
saltmarsh_code = 1
upland_code = 2
channel_code = 3

    # Elevation (DTM) in m:
elevation_path = r"my_DTM.tif"

    # Coordinate System:
crs = pyproj.CRS.from_epsg(25829) # Coordinate System EPSG code

    # Load precomputed Classifier (.joblib):
joblib_file = r"my_classifier\xgbc_best_model_joblib.joblib"
sdm = joblib.load(joblib_file) 

    # Sea Level References with regards to the Digital Elevation Model:
msl = 0.000
mnhw = 0.880
mhw = 1.137
mshw = 1.346
maht = 2.029

# Historic Suspended Matter Concentration in the main channels (Could be obtained from Copernicus Marine Service: https://data.marine.copernicus.eu/products):
historic_ss = 25.00 # Average value of SS in the main channel

# Decay constant of suspended sediment concentration with distance to channels:
decay_constant = -0.031 

# Average Accretion of saltmarsh in m/yr:
avg_accretion = 0.0059 

# Settling coefficient without vegetation:
setling_coefficient = 0.00009 # Paper: Kirwan, M. L., Guntenspergen, G. R., D’Alpaos, A., Morris, J. T., Mudd, S. M. & Temmerman, S. 2010. Limits on the adaptability of coastal marshes to rising sea level. Geophysical Research Letters, 37

# Sea Level Rise rate (m/yr) and Suspended Matter Concentration Scenario values (g/m3):
slr_rates = [0.01075] 
ss_values = [(historic_ss*2)]

# Analysis area (mask):
analysis = rasterio.open(r"my_analysis_area.tif")
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------



# ----------------------------------------------------------------- COMPUTATION OF THE BASE CONDITIONS FOR THE MODEL -----------------------------------------------------------------

# Step 1: Get Bounding Box, cellsize, transformation and nº of rows and columns of the study area (elevation has the same charateristics):
with rasterio.open(elevation_path) as elevation_data:

    elevation = elevation_data.read(1).astype(float)
    bounding_box = elevation_data.bounds

    # Pixel size:
    x_size = elevation_data.transform[0]
    y_size = abs(elevation_data.transform[4])

    # Extract the coordinates
    x_min = bounding_box.left
    x_max = bounding_box.right
    y_min = bounding_box.bottom
    y_max = bounding_box.top

    # Width and Height of the output raster:
    width = int((x_max - x_min) / x_size)
    height = int((y_max - y_min) / y_size)

    # Transformation:
    transform = from_origin(x_min, y_max, x_size, y_size)

# Reset Elevation Data:
elevation = rasterio.open(elevation_path)

# Step 2: Filter the habitat map and obtain the saltmarsh presence area:
    
    # Read the classification file, the elevation dataset and the analysis area as NumPy arrays:
analysis_data = analysis.read(1)
saltmarsh_veg = saltmarsh_vegetation.read(1)
elevation_data = elevation.read(1)

    # Filter the habitat map with the analysis area mask:
saltmarsh_vegetation_data = np.where((analysis_data==1), saltmarsh_veg, np.nan)

    # From the masked habitat map pick just the 'saltmarsh' class, if not, set to NoData:
saltmarsh_area_data = np.where((saltmarsh_vegetation_data== saltmarsh_code), saltmarsh_vegetation_data, np.nan)

    # OPTIONAL (could be commented): save the filtered saltmarsh area as .tif
""" output_path = os.path.join(out_folder, "saltmarsh_area.tif")
with rasterio.open(output_path, 'w', driver='GTiff', height=saltmarsh_area_data.shape[0], width=saltmarsh_area_data.shape[1], count=1, dtype=saltmarsh_area_data.dtype, transform=transform, crs=crs) as dst:
    dst.write(saltmarsh_area_data, 1) """


# Step 3: Compute the historic suspended concentration in the entire analysis area:

    # Filter the 'Channel' class and obtain a mask (1 = True, 0 = False):
channel_mask = (saltmarsh_vegetation_data == channel_code) 
binary_mask = np.where(channel_mask, 1.0, 0.0) # Set to 1 if 'Channel' and to 0 if not
transform = from_origin(x_min, y_max, x_size, y_size) # Set transformation

    # Create raster
binary_mask_path = os.path.join(out_folder, "channel_binary_condition_mask.tif") 
with rasterio.open(binary_mask_path, 'w', driver='GTiff', width=width, height=height, count=1, dtype=np.float32, transform=transform, crs=crs) as dst:
    dst.write(binary_mask, 1)

    # Obtain the information of the mask and open in GDAL:
channel_raster = gdal.Open(binary_mask_path, 0)
band = channel_raster.GetRasterBand(1) # Get raster information
geotransform = channel_raster.GetGeoTransform() # Set the Geotransformation

    # Create empty 'distance_to_channel.tif' raster where we will write the distance to the channels:
out_fn = os.path.join(out_folder, "distance_to_channels.tif") # Path and name
driver = gdal.GetDriverByName('GTiff') # Type of data (GeoTiff)
out_ds = driver.Create(out_fn, width, height, 1, gdal.GDT_Float32) # Create the raster in the path, with 'width' and 'height' and type of data
out_ds.SetGeoTransform(geotransform) # Define the Geotransformation to the created raster
out_ds.SetProjection(crs.to_wkt()) # Set the Coordinate System
out_band = out_ds.GetRasterBand(1) # Get raster info

    # Compute the distance to the channels and refresh the dataset. Set 'DISTUNITS=PIXEL' if you want the distance in pixel units:
gdal.ComputeProximity(band, out_band, ['DISTUNITS=GEO']) # Compute distances
out_ds.FlushCache() # Refresh dataset
out_ds = None   # Set 'out_ds' to 'None'

    # Open the result and read as NumPy Array:
distance_to_waterways = rasterio.open(out_fn)
distance_to_waterways_data = distance_to_waterways.read(1)

    # Compute and save the Historic Suspended Matter Concentration in the analysis area with 'historic suspended matter', the 'distance to Channels' and the 'decay constant':
historic_ss_saltmarsh_data = historic_ss * np.exp(decay_constant * distance_to_waterways_data)  # SSC = SSCmax * e^(-r * x)
    
    # OPTIONAL: Save the result
""" output_path = os.path.join(out_folder, "historic_suspended_matter_saltmarsh_platform.tif") # Define Path and Name
with rasterio.open(output_path, 'w', driver='GTiff', height=historic_ss_saltmarsh_data.shape[0], width=historic_ss_saltmarsh_data.shape[1], count=1, dtype=historic_ss_saltmarsh_data.dtype, transform=transform, crs=crs) as dst:
    dst.write(historic_ss_saltmarsh_data, 1)
print("Historic Suspended Matter correctly computed in the Wetland Platform") """


# Step 4: Define & compute the trapping coefficient effect of the saltmarsh
    
    # Function to read raser data:
def read_raster_data(file_path):
    with rasterio.open(file_path) as data:
        return data.read(1)
    
    # File paths to 'historic_suspended_matter_saltmarsh_platform.tif' (Historic Suspended Matter Concentration in the analysis area):
historic_ss_saltmarsh_path = os.path.join(out_folder, "historic_suspended_matter_saltmarsh_platform.tif")

    # Read as Numpy Arrays for computation:
historic_ss_saltmarsh_array = read_raster_data(historic_ss_saltmarsh_path)
elevation_array = read_raster_data(elevation_path)

    # Filter the saltmarshes that the 'Kirwan model' assume that have accetion (saltmarshes below MSHW):
floded_saltmarsh = np.where(((saltmarsh_area_data == saltmarsh_code) & ((mshw - elevation_array) > 0)), saltmarsh_code, np.nan)

    # Mask the historic suspended matter concentration with the floded saltmarshes data and compute depth with respect to MSHW where floded saltmarsh is present, if not set to NoData:
his_ss_mask = np.where((floded_saltmarsh == saltmarsh_code), historic_ss_saltmarsh_array, np.nan)
depth_mask = np.where((floded_saltmarsh == saltmarsh_code), (mshw - elevation_array), np.nan)

    # Compute the Average of both ignoring NoData values:
avg_his_ss = np.nanmean(his_ss_mask) if not np.isnan(his_ss_mask).all() else np.nan
avg_depth = np.nanmean(depth_mask) if not np.isnan(depth_mask).all() else np.nan

    # From https://doi.org/10.1016/j.scitotenv.2024.178164 dE/dt = SSC (q + S) D, compute average S (trapping_saltmarsh):
trapping_saltmarsh = (avg_accretion - (setling_coefficient * avg_his_ss * avg_depth)) / (avg_his_ss * avg_depth)
print(f"The Average C in the saltmarsh platform is: {avg_his_ss}")
print(f"The Average D in the saltmarsh platform is: {avg_depth}")
print(f"The Average Trapping effect of the Saltmarshes is: {trapping_saltmarsh}")
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------



# -------------------------------------------------------- COMPUTE THE WETLAND EVOLUTION OF THE SCENARIOS -----------------------------------------------------------------------------

# The Scenarios will be computed using Equation 4 from https://doi.org/10.1016/j.scitotenv.2024.178164

# Here we will compute yearly Accretion and every 10 years  we will update the distributions of habitat classess using the trained ML classifier (.joblib) file. 
# This way, we obtain dynamic maps according to each Sea Level Rise and Suspended Matter Scenarios:

    # Define the Time Lap of the computation (set fixed_start_year as start_year). End_year is included in the computation:
start_year = 2023
fixed_start_year = 2023
end_year = 2123

    # Create a variable to store accretion:
total_accretion = 0

    # Load elevation data and read as NumPy array:
with rasterio.open(elevation_path) as elevation_data:
    elevation = elevation_data.read(1).astype(float)

    # Compute Depth in Spring High Tides and Mean High Tides:
depth_mshw = mshw - elevation
depth_mhw = mhw - elevation

    # ---------------------------------- RUN THE SCENARIOS! -------------------------------------------------------
for slr_rate in slr_rates:
    for ss in ss_values:
        # Create a folder for the current slr_rate and ss combination
        folder_name = f"slr_{slr_rate}_ss_{ss}" # Name
        scenario_folder = os.path.join(out_folder, folder_name) # Path
        os.makedirs(scenario_folder, exist_ok=True) # If folder exists, nothing, if not, create it:
        # Reset the base conditions:
        start_year = 2023
        total_accretion = 0
        distance_to_waterways = rasterio.open(os.path.join(out_folder, "distance_to_channels.tif"))
        distance_to_waterways_data = distance_to_waterways.read(1)
        depth_mshw = mshw - elevation
        depth_mhw = mhw - elevation
        saltmarsh_vegetation_data = saltmarsh_vegetation.read(1)
        saltmarsh_veg = saltmarsh_vegetation.read(1)

        # Compute the actual suspended matter in the wetland platform:
        ss_wetland = ss * np.exp(decay_constant * distance_to_waterways_data)
        # Save the suspended matter file:
        with rasterio.open(os.path.join(scenario_folder, f"suspended_matter_saltmarsh_platform_{slr_rate}_ss_{ss}_{start_year}.tif"), 'w', driver='GTiff', height=ss_wetland.shape[0], width=ss_wetland.shape[1], count=1, dtype=ss_wetland.dtype, transform=distance_to_waterways.transform, crs=crs) as dst:
            dst.write(ss_wetland, 1) 

        # Iterate over years and compute the saltmarsh evolution model
        for year in range(start_year, end_year + 1):
            # Compute Accretion in Saltmarshes and Mudflats:
            accretion = np.where((depth_mshw >= 0) & (saltmarsh_vegetation_data == mudflat_code), (ss_wetland * setling_coefficient * depth_mshw), 0)
            accretion += np.where((depth_mshw >= 0) & (saltmarsh_vegetation_data == saltmarsh_code), (ss_wetland * (setling_coefficient + trapping_saltmarsh)  * depth_mshw), 0)
            # Aggregate Accretion in the 'total_accretion' variable:
            total_accretion = total_accretion + accretion
            # Update the Spring High Tide and Mean High Tide Depths:
            depth_mshw = depth_mshw + slr_rate - accretion
            depth_mhw = depth_mhw + slr_rate - accretion
            # Save the accretion values of each year:
            accretion_path = os.path.join(scenario_folder, f"accretion_{year}.tif")
            with rasterio.open(accretion_path, "w", driver='GTiff', height = accretion.shape[0], width = accretion.shape[1], count=1, dtype=accretion.dtype, transform=transform, crs=crs) as dst:
                dst.write(accretion, 1)

            # If 10 years have passed since the last update of the vegetation map, recalculate the predictor variables and re-predict the vegetation map.
            if ((year != start_year) and ((year - start_year + 1) % 10 == 0)):

                # Notice that the years in the filenames mean that the file is the value of the parameter during the entire year.
                # Vegetation maps are computed taking into account the predictor variables during the specified year. E.g. the Isobaths
                # of Maximum Astronomical High Tide during 2027 are computed using the reference during that year but without accounting
                # Accretion in 2027.

                # Create folders to store the results:
                step_path = os.path.join(scenario_folder, str(year))
                os.makedirs(step_path, exist_ok=True)
                after_step_path = os.path.join(scenario_folder, str(year + 1))
                os.makedirs(after_step_path, exist_ok=True)
                predictors_folder = os.path.join(after_step_path, "predictors")
                os.makedirs(os.path.join(after_step_path, "predictors"), exist_ok=True)

                # Save the total accretion. NOTICE THAT THE TOTAL ACCRETION IS THE ACCRETION BY THE END OF THE DEFINED YEAR:
                total_accretion_path = os.path.join(step_path, f"total_accretion_{year}.tif")
                with rasterio.open(total_accretion_path, 'w', driver='GTiff', height=total_accretion.shape[0], width=total_accretion.shape[1], count=1, dtype=total_accretion.dtype, transform=transform, crs=crs) as dst:
                    dst.write(total_accretion, 1)

                #Save the depth_mshw results:
                depth_mshw_result_path = os.path.join(after_step_path, f"depth_mshw_{year + 1}.tif")
                with rasterio.open(depth_mshw_result_path, 'w', driver='GTiff', height=ss_wetland.shape[0], width=ss_wetland.shape[1], count=1, dtype=ss_wetland.dtype, transform=transform, crs=crs) as dst:
                    dst.write(depth_mshw, 1)

                #Save the depth_mhw results:
                depth_mhw_result_path = os.path.join(after_step_path, f"depth_mhw_{year + 1}.tif")
                with rasterio.open(depth_mhw_result_path, 'w', driver='GTiff', height=ss_wetland.shape[0], width=ss_wetland.shape[1], count=1, dtype=ss_wetland.dtype, transform=transform, crs=crs) as dst:
                    dst.write(depth_mhw, 1)

                # COMPUTE THE PREDICTOR VARIABLES DURING THE OBJECTIVE YEAR. IN THIS CASE PREDICTOR VARIABLES ARE:
                    # 'NEW' Elevation:        
                new_elevation = total_accretion + elevation
                new_elevation_path = os.path.join(after_step_path, f"elevation_{year + 1}.tif")
                with rasterio.open(new_elevation_path, 'w', driver='GTiff', height=total_accretion.shape[0], width=total_accretion.shape[1], count=1, dtype=total_accretion.dtype, transform=transform, crs=crs) as dst:
                    dst.write(new_elevation, 1)

                    # DISTANCE TO THE MAXIMUM ASTRONOMICAL TIDE, MEAN HIGH WATER, MEAN NEAP HIGH WATER AND MEAN SEA LEVEL ISOBATHS:
                        # Open the DEM raster
                ds = gdal.Open(elevation_path)

                        # Define a function to process contour levels
                def process_contour_level(level, contour_type):
                    contour_output_path = os.path.join(after_step_path, f"isobath_{contour_type}_{round(level, 2)}_{year}".replace(".", "_") + ".shp")

                    if os.path.exists(contour_output_path):
                        ogr.GetDriverByName("ESRI Shapefile").DeleteDataSource(contour_output_path)

                    contour_out_ds = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(contour_output_path)
                    contour_out_layer = contour_out_ds.CreateLayer(f"isobath_{contour_type}_{level}")

                            # Create fields to store elevation values
                    field_defn = ogr.FieldDefn("ID", ogr.OFTInteger)
                    contour_out_layer.CreateField(field_defn)
                    field_defn = ogr.FieldDefn("Elevation", ogr.OFTReal)
                    contour_out_layer.CreateField(field_defn)

                    contour_ds = gdal.ContourGenerate(ds.GetRasterBand(1), 0, 0, [level], 0, 0, contour_out_layer, 0, 1)

                            # Create a .prj file and write the spatial reference information
                    prj_file_path = os.path.join(after_step_path, f"isobath_{contour_type}_{round(level, 2)}_{year + 1}".replace(".", "_") + ".prj")
                    with open(prj_file_path, "w") as prj_file:
                        prj_file.write('PROJCS["ETRS_1989_UTM_Zone_29N",GEOGCS["GCS_ETRS_1989",DATUM["D_ETRS_1989",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-9.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]')

                    feature_count = contour_out_layer.GetFeatureCount()
                    print(f"Computing distances to {feature_count} features...")

                            # After making any edits using ogr methods, save the changes to the shapefile using the SyncToDisk method:
                    contour_out_layer.SyncToDisk()

                            # Close the shapefile dataset:
                    contour_out_ds = None

                            # Width and Height of the output raster:
                    width = int((x_max - x_min) / x_size)
                    height = int((y_max - y_min) / y_size)

                            # Create an empty raster to store True values of Isobaths:
                    raster = np.zeros((height, width), dtype=np.float32)

                            # Load the line shapefile using GeoPandas
                    gdf = gpd.read_file(contour_output_path)

                            # Set to 1 each pixel where isobaths exist:
                    for index, row in gdf.iterrows():
                        coords = np.array(row['geometry'].coords.xy)
                        x, y = coords[0], coords[1]
                        col = np.clip(((x - x_min) / x_size).astype(int), 0, raster.shape[1] - 1)
                        row = np.clip(((y_max - y) / y_size).astype(int), 0, raster.shape[0] - 1)
                        raster[row, col] = 1.0

                            # Create a GeoTIFF to have the isobath mask:
                    transform = from_origin(x_min, y_max, x_size, y_size)
                    iso_raster_path = os.path.join(after_step_path, f"isobath_raster_{contour_type}_{round(level, 2)}_{year + 1}".replace(".", "_") + ".tif")
                    with rasterio.open(iso_raster_path, 'w', driver='GTiff', width=width, height=height, dtype=np.uint8, count=1, crs=crs, transform=transform) as dst:
                        dst.write(raster, 1)

                            # Open the mask dataset with GDAL and get the info and the geotransform:
                    iso_raster = gdal.Open(iso_raster_path, 0)
                    band = iso_raster.GetRasterBand(1)
                    geotransform = iso_raster.GetGeoTransform()

                            # Create empty proximity raster:
                    out_fn = os.path.join(predictors_folder, f"{contour_type}")
                    driver = gdal.GetDriverByName('GTiff')
                    out_ds = driver.Create(out_fn, width, height, 1, gdal.GDT_Float32)
                    out_ds.SetGeoTransform(geotransform)
                    out_ds.SetProjection(crs.to_wkt())
                    out_band = out_ds.GetRasterBand(1)

                            # Compute distance to isobaths:
                    gdal.ComputeProximity(band, out_band, ['DISTUNITS=GEO'])

                            # Close the distance raster after writing
                    out_ds = None

                            # Now open the distance raster in read mode ('r')
                    with rasterio.open(out_fn, 'r') as dst:
                        distance_value = dst.read(1)

                            # Now you can perform the corrected_distance operation. Elevations below the threshold will be set with a negative value (distance * -1) and elevations above the threshold with positive values:
                    corrected_distance = np.where(new_elevation > level, distance_value, np.where(new_elevation < level, (distance_value * (-1)), 0))

                            # Avoid -0 values and set to 0 in case they exist:
                    corrected_distance = np.where(corrected_distance != -0, corrected_distance, 0)

                    # Open the distance raster again in write mode ('w') to save the corrected distance
                    with rasterio.open(out_fn, 'w', driver='GTiff', width=width, height=height, dtype=np.float32, count=1, crs=crs, transform=transform) as dst:
                        dst.write(corrected_distance, 1)

                # Contour levels (set those ones important as predictor variables):
                contour_levels = [  
                    #(msl + (slr_rate * (year - fixed_start_year +1))),
                    (mhw + (slr_rate * (year - fixed_start_year + 1))),
                    (mnhw + (slr_rate * (year - fixed_start_year + 1))),
                    (maht + (slr_rate * (year - fixed_start_year + 1))),
                    (mshw + (slr_rate * (year - fixed_start_year + 1)))
                ]

                # Obtain all the corrected distance to Isobaths iterating the 'contour levels and contour types':
                contour_types = [ "distance_to_MHW_contour_corrected.tif", "distance_to_MNHW_countour_corrected.tif", "distance_to_MAHT_contour_corrected.tif", "distance_to_MSHW_countour_corrected_25829.tif"]
                for level, contour_type in zip(contour_levels, contour_types):
                    process_contour_level(level, contour_type)

                # Elevation related to MHW (other predictor):
                elev_related_mhw = new_elevation - (mhw + (slr_rate * (year - fixed_start_year + 1)))
                elev_related_mhw_path = os.path.join(predictors_folder, f"elevation_related_to_MHW_25830.tif")
                with rasterio.open(elev_related_mhw_path, 'w', driver='GTiff', height=total_accretion.shape[0], width=total_accretion.shape[1], count=1, dtype=total_accretion.dtype, transform=transform, crs=crs) as dst:
                    dst.write(elev_related_mhw, 1)

                print("Now we have all the new predictor rasters in the timestep folder/predictors...")

                # Predictor paths:
                raster_predictors = [
                    elev_related_mhw_path,
                    os.path.join(predictors_folder, contour_types[0]),
                    os.path.join(predictors_folder, contour_types[1]),
                    os.path.join(predictors_folder, contour_types[2]),
                    os.path.join(predictors_folder, contour_types[3])
                    #os.path.join(predictors_folder, contour_types[4])
                ]
                print("{} raster predictors will be used in the computation".format(len(raster_predictors)))
                print(raster_predictors)

                # Prepare the pyimpute workflow to run the SDM:
                print("Preparing pyimpute workflow...")
                # Load targets
                target_xs, raster_info = load_targets(raster_predictors)
                print("Pyimpute workflow prepared!")

                # Perform imputations using the joblib model
                impute(target_xs, sdm, raster_info, outdir=after_step_path, class_prob=True, certainty=True)

                # Set the result as the 'Wetland Vegetation' class file and filter it:
                    # Vegetation:
                saltmarsh_vegetation = rasterio.open(os.path.join(after_step_path, "responses.tif"))
                saltmarsh_veg_np = saltmarsh_vegetation.read(1)

                    # New Elevation Data:
                step_elevation = rasterio.open(new_elevation_path)
                step_elevation_data = step_elevation.read(1)
                
                # COMPUTE THE DISTANCE TO THE NEW CHANNEL CLASS:
                    # Filter the analysis area:
                saltmarsh_vegetation_data = np.where((analysis_data==1), saltmarsh_veg_np, np.nan)
                    # Filter the channel class. Set to 1 True, 0 False:
                channel_mask = (saltmarsh_vegetation_data == channel_code)
                binary_mask = np.where(channel_mask, 1.0, 0.0)
                    # Redefine the transformation:
                transform = from_origin(x_min, y_max, x_size, y_size)

                    # Save the binary mask as a GeoTIFF:
                binary_mask_path = os.path.join(after_step_path, f"channel_binary_condition_mask_{year + 1}.tif")
                with rasterio.open(binary_mask_path, 'w', driver='GTiff', width=width, height=height, count=1, dtype=np.float32, transform=transform, crs=crs) as dst:
                    dst.write(binary_mask, 1)

                    # Compute the distance to Channels:
                channel_raster = gdal.Open(binary_mask_path, 0)
                band = channel_raster.GetRasterBand(1)
                geotransform = channel_raster.GetGeoTransform()

                    # Create empty distance raster:
                out_fn = os.path.join(after_step_path, f"distance_to_channels_{year + 1}.tif")
                driver = gdal.GetDriverByName('GTiff')
                out_ds = driver.Create(out_fn, width, height, 1, gdal.GDT_Float32)
                out_ds.SetGeoTransform(geotransform)
                out_ds.SetProjection(crs.to_wkt())
                out_band = out_ds.GetRasterBand(1)
                
                    # Compute distance to Channels:
                gdal.ComputeProximity(band, out_band, ['DISTUNITS=GEO'])

                    # Refresh:
                out_ds.FlushCache()

                    # Close the resulting raster:
                out_ds = None

                    # Open the resulting raster again and read as NumPy Array. In this way 'ss_wetland' is computed with the new distance to channels:
                distance_to_waterways = rasterio.open(out_fn)
                distance_to_waterways_data = distance_to_waterways.read(1)

                    # Compute the new Suspended Matter in the wetland:
                ss_wetland = ss * np.exp(decay_constant * distance_to_waterways_data)
                
                    # Save the result of the suspended matter:
                with rasterio.open(os.path.join(after_step_path, f"suspended_matter_saltmarsh_platform_{slr_rate}_ss_{ss}_{year + 1}.tif"), 'w', driver='GTiff', height=ss_wetland.shape[0], width=ss_wetland.shape[1], count=1, dtype=ss_wetland.dtype, transform=distance_to_waterways.transform, crs=crs) as dst:
                    dst.write(ss_wetland, 1)

print("Modelling computed!")