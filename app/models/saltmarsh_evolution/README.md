# Saltmarsh Evolution under Sea Level Rise and Suspended Sediment Change

## About the folder

This work includes the scripts to replicate [Egidazu-de la Parte *et al*, 2025](https://doi.org/10.1016/j.scitotenv.2024.178164) results and methodology. Scripts can be run together to replicate the Integrated Marsh Evolution Model described by [Egidazu-de la Parte *et al*, 2025](https://doi.org/10.1016/j.scitotenv.2024.178164). The Integrated Marsh Evolution Model combines a process-based model ([Kirwan and Murray, 2007](https://doi.org/10.1073/pnas.0700958104)) and a machine learning algorithm (XGBoost) to better simulate future marsh distributions under potential changes of sea level rise and suspended sediment change. This integration not only simulates the evolution of the system over time but also accounts for the non-linear eco-geomorphic interactions that may alter the landscape during that period. For more detailed information see [Egidazu-de la Parte *et al*, 2025](https://doi.org/10.1016/j.scitotenv.2024.178164).

## Replicating the project

This GitHub repository contains the codes and datasets needed to replicate the results described by [Egidazu-de la Parte *et al*, 2025](https://doi.org/10.1016/j.scitotenv.2024.178164). You can clone it to your computer and and use the 'requirements-local-windows.txt' to install all the requirements in a virtual environment. Make sure you have python 3.11 installed in your computer. The following steps can be run to clone the repository and create the virtual environment with the needed requirements:

1. Open the Command Prompt
2. ´ git clone https://github.com/begidazu/MESAT.git´
3. ´cd <repo>´
4. ´python3.11 -m venv venv´
5. ´venv\Scripts\activate.bat´
6. ´pip install -r requirements.txt´