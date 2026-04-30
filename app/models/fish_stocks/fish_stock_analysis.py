# This code is used to analyse and obtain the results for the fish stock section.
import os
from sdm_analysis import SDMFileManager, compute_presence_absence, create_presence_absence_table, graph_stocks, create_stock_index_table_from_suitability

# Results working directory. Parent directory where all results of SDMs are and where all output will be saved:
results_dir = r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct"

# SDMs working directory. Working directory where all SDM files are:
sdms_dir = os.path.join(results_dir, "SDMs")

# Presence/Absence output directory (it is created if it does not exist):
presence_absence_dir = os.path.join(results_dir, "presence_absence")

# Initialize the SDM file manager
sdm_manager = SDMFileManager(sdms_dir)

# #Run presence/absence maps:
# compute_presence_absence(
#     sdm_manager,
#     presence_absence_dir,
#     taxon_ids=['126426'],
#     #taxon_ids=['126421', '126426', '126822', '127023'],
#     methods=['ensemble'],
#     scenarios=['2000_2010', '2010_2020'],
#     #scenarios=['2000_2010', '2010_2020'],
#     thresholds=['max_spec_sens']
# )

# #Create presence/absence table:
# extent_table = create_presence_absence_table()

# #Save table to csv:
# extent_table.to_csv(os.path.join(results_dir, "extents_table.csv"))

# Print stock graphs and save the plots:
graph_stocks(excel_file=r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct\stock_indicators2.xlsx",
             sheet_name=["ANE8", "ANE9AS", "PIL8C9A", "HOM9A", "HOMNEA", "MACNEA"],
             sheet_labels={
                 "ANE8": "A",
                 "ANE9AS": "B",
                 "PIL8C9A": "C",
                 "HOM9A": "D",
                 "HOMNEA": "E",
                 "MACNEA": "F"
             },
             x="Year",
             x_label="Year",
             #y=["OverallCondition"],
             y=["ReproductiveCapacity", "RecruitmentRatio", "SustainableFoodProvisioning", "SustainableExploitation", "AbioticStatus"],
             y_label= "Condition Indicator scores",
             # color_sheet = ['#0764E6', "#07E6D9", "#366663", "#E57A06", "#664F36", "#364A66"],
             color_y = ["#DD0000", "#00A59DFF", "#2AB126", "#F9FD04", "#7641DA"],
             year_column="Year",
             year_range=(2000,2019),
             title="Stock Condition Indicators",
             figsize=(12, 6),
             show_plot=False,
             combine_sheets=True,
             use_subplots=True,
             y_names_dict={
                 "ReproductiveCapacity": "RC",
                 "RecruitmentRatio": "RR",
                 "SustainableFoodProvisioning": "SFP",
                 "SustainableExploitation": "SE",
                 "AbioticStatus": "AS"
             },
             show_legend=True,
             save_path=os.path.join(r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct\Graphs", "stock_condition_indicators_subplots_acronyms.png")
            )

# TAXON_CONFIG = {
#         #     'species_name': 'Trachurus trachurus',
#         #     'stocks': [
#         #         #('Trachurus trachurus in Atlantic Iberian waters', r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\hom_27_9a.shp"),
#         #         ('Trachurus trachurus in Northeast Atlantic and adjacent waters', r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\hom_27_2a3a4a5b6a7a__ce_k8.shp")
#         #     ]
#         # },
#         127023: {
#             'species_name': 'Scomber scombrus',
#             'stocks': [
#                 ('Scomber scombrus in Northeast Atlantic and adjacent waters', r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Data_nca2\Stock_ICES_Areas\mac_27_nea.shp")
#             ]
#         }
#     }

# TIMEFRAMES = {
#     "2000_2010": "2000 - 2010",
#     "2010_2020": "2010 - 2020",
# }

# abiotic_state_table = create_stock_index_table_from_suitability(sdm_manager=sdm_manager, presence_absence_base=r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct\presence_absence", taxon_config=TAXON_CONFIG, timeframes=TIMEFRAMES, method="ensemble", threshold="max_spec_sens", print_esref=True)

# abiotic_state_table.to_csv(os.path.join(r"C:\Users\beñat.egidazu\Desktop\NAS\PhD\Papers\Fisheries_2\Results_correct", "abiotic_state_indicator_table_other_3stocks.csv"), index=False)