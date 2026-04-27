# This code is used to analyse and obtain the results for the fish stock section.
import os
from sdm_analysis import SDMFileManager, compute_presence_absence, create_presence_absence_table, graph_stocks

# Results working directory. Parent directory where all results of SDMs are and where all output will be saved:
results_dir = r"path\to\results"

# # SDMs working directory. Working directory where all SDM files are:
# sdms_dir = os.path.join(results_dir, "SDMs")

# # Presence/Absence output directory (it is created if it does not exist):
# presence_absence_dir = os.path.join(results_dir, "presence_absence")

# # Initialize the SDM file manager
# sdm_manager = SDMFileManager(sdms_dir)


# # Run presence/absence maps:
# compute_presence_absence(
#     sdm_manager,
#     presence_absence_dir,
#     taxon_ids=['126421', '126426', '126822'],
#     methods=['ensemble'],
#     scenarios=['2000_2010', '2010_2020'],
#     thresholds=['max_spec_sens']
# )

# # Create presence/absence table:
# extent_table = create_presence_absence_table()

# # Save table to csv:
# extent_table.to_csv(os.path.join(results_dir, "extents_table.csv"))

# Print stock graphs and save the plots:
graph_stocks(excel_file=r"pat\to\excell\stock_info.xlsx",
             sheet_name="hom27.9a_2025",
             x="Year",
             x_label="Year",
             y=["ReproductiveCapacity", "RecruitmentRatio", "RelativeGrowth", "SustainableExploitation", "GoodEnvironmentalStatus"],
             y_label= "Indicator Value",
             color = ['green', "orange", "blue", "red", "brown"],
             year_column="Year",
             year_range=(2000,2020),
             title="Trachurus trachurus Stock Indicators in Division 9a",
             figsize=(12, 6),
             show_plot=False,
             save_path=os.path.join(r"pat\to\saving\folder", "name.png")
            )