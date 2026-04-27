import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import numpy as np
from scipy.stats import kurtosis, skew
import pandas as pd

workspace = r"path\to\workspace"

# ----------------- BOXPLOT OF THE ROC AUC SCORES IN THE OUTER LOOP OF NESTED-CV BY CASE STUDY -----------------

# # Boxplots for ROC AUC Score of the case studies:

#     # ROC AUC Score values of each case study in the outer loop of Nested Cross-Validation
# oka_estuary = [0.98363326, 0.96767564, 0.94760892, 0.9527472,  0.98515264, 0.93793269,
#                 0.94709055, 0.95779617, 0.94550345, 0.97496817, 0.93210414, 0.9820957, 
#                 0.96896455, 0.98902581, 0.93461651, 0.99306442, 0.94979557, 0.94970622,
#                 0.95875844, 0.96134778, 0.9922696,  0.95955752, 0.9347786, 0.9920736, 
#                 0.94900785]
# santona_estuary = [0.95265902, 0.95173488, 0.96005414, 0.94422702, 0.93469252, 0.95096402,
#                    0.93394109, 0.98778463, 0.9398258,  0.96403811, 0.87325738, 0.98075527,
#                    0.95313605, 0.96166884, 0.94290185, 0.90739997, 0.97390681, 0.95882399,
#                    0.98477691, 0.97175897, 0.96044502, 0.91176322, 0.96428638, 0.95372457,
#                    0.96421301]
# puerto_real = [0.98480527, 0.98601589, 0.99046139, 0.98196124, 0.98735196, 0.98644968,
#                0.9857007,  0.98599973, 0.98973818, 0.99113103, 0.98993583, 0.98284011,
#                0.98753122, 0.98404861, 0.99146186, 0.98766652, 0.97914144, 0.98614381,
#                0.98931378, 0.99264107, 0.98749433, 0.98847045, 0.98827073, 0.98256432,
#                0.98682394] # THIS ARE THE RESULTS OF THE 5 PREDICTOR MODEL

#     # Print average ROC AUC Scores of each case study and the std deviation:
# print("The average ROC AUC score of the Oka Estuary is: {avg} +- {std}".format(avg = np.mean(oka_estuary), std = np.std(oka_estuary)))
# print("The average ROC AUC score of the Santander saltmarshes is: {avg} +- {std}".format(avg = np.mean(santona_estuary), std = np.std(santona_estuary)))
# print("The average ROC AUC score of Puerto Real is: {avg} +- {std}".format(avg = np.mean(puerto_real), std = np.std(puerto_real)))

#     # Combine all data:
# all_data = [oka_estuary, santona_estuary, puerto_real]

#     # Set the color of the box outline to dark blue
# boxprops = dict(linestyle='-', linewidth=1, color='darkblue')

#     # Create a Boxplot with all the cases:
# plt.boxplot(all_data, labels=['Oka estuary', 'Santander Bay', 'Puerto Real'], boxprops=boxprops, showfliers=False)

#     # Add labels and title
# plt.xlabel('Study Sites')
# plt.ylabel('Macro-averaged ROC AUC Scores')
# #plt.title('Boxplot for Different Cases')

#     # Show the plot
# plt.show()

# ----------------------------------------------------------------------------------------------------------------


# ----------------------------- STACKED 100% BAR CHART FOR RELATIVE AREAS OVER TIME  -----------------------------

# # We can compute the areas and/or cell counts of all the classes over time using the ArcGIS Pro tool 
# # 'Zonal Statistics as Table' from the Spatial Analyst Extension. Then we can import it as .csv and work
# # with the results with Pandas. In this case we will create a workflow to create Stacked 100% Bar Charts 
# # to compare relative areas of the classes over time. The .csv should have, at least, the following fields:
# # 1- 'class', 2- 'relative_area' , 3- 'year', 4- 'scenario'


# # Datasets with the 'Class', 'Relative Areas', 'Year of measure' & 'Scenario': 
#     # Folder where the .csv are stored:
# areas_folder = r"C:\Users\beñat.egidazu\Desktop\PhD\Papers\Saltmarshes\Results\Areas\Oka"

#     # Directory of the .csv s:
# csv_directory = {
#     'oka_reg_rcp45_8g': os.path.join(areas_folder, 'reg_rcp45_8g_classes.csv'),
#     'oka_reg_rcp45_17g': os.path.join(areas_folder, 'reg_rcp45_17g_classes.csv'),
#     'oka_reg_rcp45_34g': os.path.join(areas_folder, 'reg_rcp45_34g_classes.csv'),
#     'oka_reg_rcp85_8g': os.path.join(areas_folder, 'reg_rcp85_8g_classes.csv'),
#     'oka_reg_rcp85_17g': os.path.join(areas_folder, 'reg_rcp85_17g_classes.csv'),
#     'oka_reg_rcp85_34g': os.path.join(areas_folder, 'reg_rcp85_34g_classes.csv'),
#     'oka_glo_rcp45_8g': os.path.join(areas_folder, 'glo_rcp45_8g_classes.csv'),
#     'oka_glo_rcp45_17g': os.path.join(areas_folder, 'glo_rcp45_17g_classes.csv'),
#     'oka_glo_rcp45_34g': os.path.join(areas_folder, 'glo_rcp45_34g_classes.csv')   
# }
#     # Names of scenarios:
# scenarios = ['oka_reg_rcp45_8g', 'oka_reg_rcp45_17g', 'oka_reg_rcp45_34g',
#              'oka_reg_rcp85_8g', 'oka_reg_rcp85_17g', 'oka_reg_rcp85_34g',
#              'oka_glo_rcp45_8g', 'oka_glo_rcp45_17g', 'oka_glo_rcp45_34g']

#     # Create the 'Big' plot:
# fig, ax = plt.subplots(nrows = 3, ncols = 3, sharex = True, sharey = True, squeeze = False, figsize=(10, 10),
#                        subplot_kw = {'ymargin': 0.00, 'xmargin': -0.4})

#     # Add y-axis text:
# fig.text(0.02, 0.5, 'Relative Area (%)', va='center', rotation='vertical', fontsize=14)

#     # Add x-axis text:
# fig.text(0.5, 0.035, 'Year', ha= 'center', fontsize = 14)

#     # Set custom colors for each class
# class_colors = {'Mudflat': '#9D5709', 'Saltmarsh': '#0D7800', 'Upland Area': '#C2C2C2', 'Channel': '#09B3F3'}


#     # Graph positions:
# graph_pos = {
#     'oka_reg_rcp45_8g': ax[0, 0],
#     'oka_reg_rcp45_17g': ax[0, 1],
#     'oka_reg_rcp45_34g': ax[0, 2],
#     'oka_reg_rcp85_8g': ax[1, 0],
#     'oka_reg_rcp85_17g': ax[1, 1],
#     'oka_reg_rcp85_34g': ax[1, 2],
#     'oka_glo_rcp45_8g': ax[2, 0],
#     'oka_glo_rcp45_17g': ax[2, 1],
#     'oka_glo_rcp45_34g': ax[2, 2],
# }

# # Plot the Relative Areas as Stacked 100% Bar Charts in their corresponding subplot:
# for csv in scenarios:

#     # Subplot position:
#     position = graph_pos.get(csv)

#     # Read the .csv files as dataframes and keep just the needed fields:
#     dataframe = pd.read_csv(csv_directory.get(csv))
#     cleaned_dataframe = dataframe[['class', 'relative_area', 'year', 'scenario']]

#     # Pivot the csv to have the good structure. 'relative_area' as values, 'class' as columns and 'year' as rows:
#     pivoted_dataframe = cleaned_dataframe.pivot_table(values='relative_area', columns='class', index='year', aggfunc= 'sum')

#     # Plot the pivoted csv file dataframe in the correct position:
#     pivoted_dataframe.plot.bar(stacked = True, ax= position, color = [class_colors.get(c, '#999999') for c in pivoted_dataframe.columns],
#                                width=1, edgecolor='black', legend=None)

#     # Remove x-axis labels ('year') for the last row:
#     if position in [ax[2, 0], ax[2, 1], ax[2, 2]]:
#         position.set_xlabel('')
#         # Keep just some positions of the years:
#         tick_labels = ['2017', None, '2037', None, '2057', None, '2077', None, '2097', None, '2117']
#         position.set_xticklabels(labels = tick_labels, rotation = 45)
    
#     # Add titles in the first row (Suspended Sediment Concentrations):
#     if position in [ax[0,0]]:
#         position.set_title('8.5 mg/L', fontdict= {'fontweight': 'black', 'fontsize': 10})    
#     if position in [ax[0,1]]:
#         position.set_title('17 mg/L', fontdict= {'fontweight': 'black', 'fontsize': 10})
#     if position in [ax[0,2]]:
#         position.set_title('34 mg/L', fontdict= {'fontweight': 'black', 'fontsize': 10})
        
#     # Add titles in the first column (Sea Level Rise rates):
#     if position in [ax[0,0]]:
#         position.text(s = '23 cm/century', x = -4, y = 18, fontsize= 10, fontweight= 'black', rotation = 90)
#     if position in [ax[1,0]]:
#         position.text(s = '52 cm/century', x = -4, y = 18, fontsize = 10, fontweight = 'black', rotation = 90)
#     if position in [ax[2,0]]:
#         position.text(s='103 cm/century', x = -4, y = 15, fontsize = 10, fontweight = 'black', rotation = 90) 

# # Set the spacing between the subplots (wspace: width space, hspace: height space):
# plt.subplots_adjust(wspace=0.05, hspace=0.1)

# # Save the figure as PNG in the areas_folder:
# plt.savefig(os.path.join(areas_folder, 'Oka_relative_areas.png'), dpi = 300)

# # Show the plot:
# plt.show()

# ------------------------------------------------------------------------------------------------------------------




# -------------------------------- BAR CHART FOR FEATURE IMPORTANCE PLOTS ----------------------------------------

# # Values of Features according to each case study during the Recursive Feature Elimination process:
# # Order of the values are: dist_fres, elev_MHW, dist_MAT, dist_MSHW, dist_MHW, dist_MNHW, dist_MSL

# # irish_sea = {
# #     'distance freshwater': 0,
# #     'DTM related to MHT': 0,
# #     'distance to MAHT': 0,
# #     'distance to MSHT': 0,
# #     'distance to MHT': 0,
# #     'distance to MNHT': 0,
# #     'distance to MSL': 0
# # }

# oka_estuary = {
#     'distance freshwater': 0.0669,
#     'DTM related to MHT': 0.2605,
#     'distance to MAHT': 0.1711,
#     'distance to MSHT': 0.1342,
#     'distance to MHT': 0.1370,
#     'distance to MNHT': 0.1097,
#     'distance to MSL': 0.1206
# }

# ih_cantabria = {
#     'distance freshwater': 0,
#     'DTM related to MHT': 0.3339,
#     'distance to MAHT': 0.0829,
#     'distance to MSHT': 0.1116,
#     'distance to MHT': 0.1150,
#     'distance to MNHT': 0.2007,
#     'distance to MSL': 0.1559
# }

# cadiz_bay = {
#     'distance freshwater': 0,
#     'DTM related to MHT': 0.2360, 
#     'distance to MAHT': 0.1266,
#     'distance to MSHT': 0.1069,
#     'distance to MHT': 0.2220,
#     'distance to MNHT': 0.2045,
#     'distance to MSL': 0.1040
# }


# # Create the 'Big' plot:
# fig, ax = plt.subplots(nrows=1, ncols=3, sharex=True, sharey=True, squeeze=False, figsize= (8,6))

# # Add x-axis and y-axis:
# fig.text(x= 0.5, y= 0.075, s='Predictor Variables', ha='center', fontsize = 12)
# fig.text(x= 0.02, y= 0.5, s='Feature Importance', va='center', rotation= 'vertical', fontsize = 12)

# # Values, Predictors and position of subplots:
# SUBPLOTS = {
#     #'irish': {'values': irish_sea, 'position': ax[0,0]},
#     'oka': {'values': oka_estuary, 'position': ax[0,0]},
#     'cantabria': {'values': ih_cantabria, 'position': ax[0,1]},
#     'cadiz': {'values': cadiz_bay, 'position': ax[0,2]}
# }

# colors = ['#070647', '#1D31B0', '#0762C2', '#00939A', '#03CB52', '#7ADC0C', '#FEF71C']


# # Loop through the subplots dictionary to add graphs to the subplots:
# for case_study, info in SUBPLOTS.items():
    
#     # Get subplot position, labels of predictors and values of each predictor: 
#     position = info['position']
#     values = list(info['values'].values())
#     predictors = list(info['values'].keys())

#     # Plot the subplots in their location:
#     position.bar(predictors, values, color= colors)
#     # Hide the predictors labels as we will use a Legend for this purpose, if not, delete the plt.legend() code:
#     position.set_xticklabels(labels = predictors, rotation = 45, fontsize = 8, visible = False, minor = False)
#     # Hide the ticks ob the x-axis:
#     position.tick_params(bottom= False)
    
#     # Add case study 'codes' to each subplot:
#     # if position is ax[0,0]:
#     #     position.text(s='A', x= 0.025, y=0.9, fontsize= 14, fontweight= 'black', transform=position.transAxes)
#     if position is ax[0,0]:
#         position.text(s='A', x= 0.025, y=0.95, fontsize= 16, fontweight= 'black', transform=position.transAxes)
#     if position is ax[0,1]:
#         position.text(s='B', x= 0.025, y=0.95, fontsize= 16, fontweight= 'black', transform=position.transAxes)
#     if position is ax[0,2]:
#         position.text(s='C', x= 0.025, y=0.95, fontsize= 16, fontweight= 'black', transform=position.transAxes)

# # Set the spacing between the subplots (wspace: width space, hspace: height space):
# plt.subplots_adjust(wspace=0.05, hspace=0.1)

# # Legend colors and labels:
# d_fresh = mpatches.Patch(color = '#070647', label = 'distance to Freshwater')
# ele_mhw = mpatches.Patch(color = '#1D31B0', label = 'Elevation related to MHW')
# d_maht = mpatches.Patch(color = '#0762C2', label = 'distance to MAHT')
# d_msht = mpatches.Patch(color = '#00939A', label = 'distance to MSHT')
# d_mht = mpatches.Patch(color = '#03CB52', label = 'distance to MHT')
# d_mnht = mpatches.Patch(color = '#7ADC0C', label = 'distance to MNHT')
# d_msl = mpatches.Patch(color = '#FEF71C', label = 'distance to MSL')
# plt.legend(handles = [d_fresh, ele_mhw, d_maht, d_msht, d_mht, d_mnht, d_msl], loc= 'lower right', fontsize = 8, framealpha = 1.0)

# # Save the plot:
# plt.savefig(os.path.join(workspace, 'feature_importances.png'), dpi=300)

# --------------------------------------------------------------------------------------------------------------------------------------