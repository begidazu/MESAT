Sub-ecosystem components: Macrozoobenthos (Hamon grab) and macrozoobenthos (Day grab)

Macrozoobenthos split into two sub-components depending on sampling gear (Hamon grab � for mixed/coarse sediment, Day grab � for fine or homogenous sediment)

Data sources:
- Hamon grab: OneBenthic Baseline Tool - grabcore sample data, Cefas 
- Day grab: OneBenthic Baseline Tool - grabcore sample data, Cefas; Benthos monitoring in the marine environment, Marine Institute (only presence/absence data due to missing abundance data from MI)
Timeframe: 
- 2012-2022 (no overlapping sites to compare in time series)

Type of data: grabcore data (monitoring and EIA studies; high quality data)
Links: https://rconnect.cefas.co.uk/onebenthic_dataextractiongrabcore/ ; https://data.gov.ie/dataset/benthos-monitoring-in-the-marine-environment [available on request from Marine Institute]



*All species (716 for Hamon grab, 449 for Day grab)
*Locally rare species (528 for Hamon grab, 314 for Day grab), as calculated for the BBT (species present within the 5% of the populated cells)
*Regionally and nationally rare species not included in the calculations (as for the RRF, they constitute almost 100% of all species in the Hamon dataset including species that are common in the region like M. edulis, which is not credible; for this reason and time constraints RRF and NRF were not included)


*Ecologically significant species (6): Alcyonium digitatum, Asterias rubens, Cerastoderma edule, Hippolyte varians, Psammechinus miliaris, Virgularia mirabilis
*Habitat-forming/biogenic species (5): Arenicola marina, Lanice conchilega, Modiolus modiolus, Mytilus edulis, Sabellaria spinulosa
*Symbiotic species (8): Acholoe squamosa, Adamsia palliata, Anapagurus laevis, Astropecten irregularis, Pagurus alatus, Pagurus bernhardus, Pagurus cuanensis, Pagurus prideaux


EVA calculated as per R script from VLIZ
HAMON: (11) AQs answered: 1-2,7-15, all relevant to macrozoobenthos
DAY: (7) AQs answered: 1,7,10,12,14, all relevant to macrozoobenthos


-------
Changes (ver. August 2024):
Calculations previously were made for entire area of the BBT rather than sea polygons � that was corrected. For the shp file, the view displayed is the SEA area (land polygons removed, separate file with land polygons can be provided if needed)

Changes (ver. December 2024):
Corrected EV calculations (instead of means, max values was used in the final assessment of each cell); confidence assessment using quantiles

------

HAMON GRAB
All cells (final number of sea-covering cells in the BBT, includes cells with no data): 368,632
Populated cells / all cells (data coverage %): (358/368,632)*100 = 0.1%

DAY GRAB
All cells (final number of sea-covering cells in the BBT, includes cells with no data): 368,632
Populated cells / all cells (data coverage %): (233/368,632)*100 = 0.06%


Also, AQs 3-6 (related to NRF and RRF) were removed

-------
Confidence assessment:
Calculated in R 

HAMON GRAB
*based on the min. (2)- max. (129) recordings per cell 
*358 cells with data assessed 
*11 out of 15 AQs answered

DAY GRAB
*based on the min. (3)- max. (362) recordings per cell 
*233 cells with data assessed 
*7 out of 15 AQs answered
