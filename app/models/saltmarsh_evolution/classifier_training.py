import os
import shutil
import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd 
from pyimpute import load_training_vector, load_targets, impute
import joblib
from sklearn.model_selection import RandomizedSearchCV, cross_val_score, StratifiedKFold, RepeatedStratifiedKFold
from scipy.stats import uniform as sp_randFloat, randint as sp_randInt
from sklearn.multiclass import OneVsOneClassifier 
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import confusion_matrix, roc_auc_score, classification_report, make_scorer
from sklearn.feature_selection import RFECV
from shapely.geometry import Point

#Input and Output workspaces: 
my_workspace = r"my_path" 
input_folder = os.path.join(my_workspace, "inputs")
output_folder = os.path.join(my_workspace, "outputs")

# Create 'Input' & 'Output' folders in the workspace if they are not available:
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Import the sample data:
sample_path = r"sample_data"
sample_data = gpd.GeoDataFrame.from_file(sample_path)

# Convert the Geopandas DataFrames X_df (descriptors) and Y_df (response) variables:
X_df = sample_data.loc[:, ["elev_MHT", "dist_MAT", "dist_mshw", "dist_MNHW", "dist_MSL", "dist_MHW"]]   # Field names with the predictor variables
y_df = sample_data["class"].values.ravel()  # Target habitats/categories
print(X_df)

#------------------------------------------------------------- THE FIRST PART OF THE CODE CONDUCTS FEATURE SELECTION -------------------------------------------------------------------

# ------ IN THE FOLLOWING PIECE OF CODE WE WILL REDUCE THE NUMBER OF DESCRIPTOR VARIABLES FOR OUR FINAL Species Distribution Model/Machine Learning classifier -----------------------

# Step 1: Define the Random Forest Classifier for feature selection:
rf_classifier = RandomForestClassifier(random_state=1)

# Scorer for feature selection:
roc_auc_scorer = make_scorer(roc_auc_score, needs_proba=True,  average='macro', multi_class='ovo')

# Step 2: Perform Recursive Feature Elimination with Cross-Validation (RFECV)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=1)  # Define nº of splits and other configurations
rfecv = RFECV(estimator=rf_classifier, step=1, cv=cv, scoring=roc_auc_scorer)   # Configure the RFECV
rfecv.fit(X_df, y_df)   # Fit the model

# Step 3: Print feature importances:
print("Feature Importances:")
for feature, importance in zip(X_df.columns, rfecv.estimator_.feature_importances_):
    print(f"{feature}: {importance:.4f}")

# Step 4: Plot accuracy vs. number of features and save it:
plt.figure(figsize=(10, 6))

    # Plot Macro Average ROC AUC Score values for each split using Seaborn
for i in range(5):  # Assuming 5 splits
    sns.scatterplot(x=range(1, len(rfecv.cv_results_['mean_test_score']) + 1), y=rfecv.cv_results_[f'split{i}_test_score'], marker='o', alpha=0.5, label=f'Split {i+1}')

    # Plot Macro Average ROC AUC Score splits
sns.lineplot(x=range(1, len(rfecv.cv_results_['mean_test_score']) + 1), y=rfecv.cv_results_['mean_test_score'], color='b', linewidth=2, label='Mean Accuracy')
plt.xlabel("Number of selected Predictors ")
plt.ylabel("Macro-average ROC AUC Score")
plt.ylim(0.7, 1)  # Set Y axis limits from 0.7 to 1
plt.legend(title='Splits', loc='lower right')
plt.title("Cross-Validated ROC AUC Score vs. Number of Features")
plt.grid()

    #Save the graphic in a PNG file:
plot_filename = os.path.join(output_folder, "cv_accuracy_n_features.png")
plt.savefig(plot_filename)

# Step 5: plot feature importance as a bar plot

    # Custom labels for specific features
custom_labels = {
    'dist_fresh': 'Distance to\nFreshwater Inputs',
    'dist_OSM_c': 'Distance to Open Street\nMap coastline',
    'elev_MHT': 'Elevation related to\nMean High Tide',
    'slope': 'Slope',
    'dist_MAT': 'Distance to Maximum\nAstronomical Tide contour',
    'dist_mshw': 'Distance to Mean\nSpring High Tide Contour',
    'dist_MHW': 'Distance to Mean High\nTide contour',
    'dist_MNHW': 'Distance to Mean Neap\nHigh Tide contour',
    'dist_MSL': 'Distance to Mean Sea\nLevel contour'
    # Add more custom labels as needed
}

    # Rename DataFrame columns to match custom labels
X_df_renamed = X_df.rename(columns=custom_labels)

    # Plot feature importance as a bar plot with custom X-axis labels
plt.figure(figsize=(15, 11))
sns.barplot(x=X_df_renamed.columns, y=rfecv.estimator_.feature_importances_)
plt.xticks(rotation=45, ha='right', fontsize=7)
plt.xlabel("Features")
plt.ylabel("Feature Importance")
plt.title("Feature Importance")
plt.grid()

    # Save the feature importance graphic in a PNG file:
feature_importance_filename = os.path.join(output_folder, "feature_importance.png") # Save predictor importance plot
plt.savefig(feature_importance_filename)

# Step 6: Select the N most important features 
num_features_to_keep = 6    # Notice that this should be based on the previous two plots
selected_feature_indices = np.argsort(rfecv.estimator_.feature_importances_)[::-1][:num_features_to_keep]
selected_features = X_df.columns[selected_feature_indices]

# Step 7: Create the resulting GeoDataFrame with the N most important features plus the "class" field
selected_features = np.append(selected_features, "class")
resulting_gdf = sample_data[selected_features]

# Merge the geometry from 'sample_data' back into the 'resulting_gdf'
resulting_gdf['geometry'] = sample_data['geometry'].apply(Point)

# Display the resulting GeoDataFrame
print("\nResulting GeoDataFrame:")
print(resulting_gdf)

# Save the resulting GeoDataFrame as a shapefile
shapefile_path = os.path.join(output_folder, "resulting_gdf.shp")
resulting_gdf = gpd.GeoDataFrame(resulting_gdf, geometry='geometry')
resulting_gdf.to_file(shapefile_path)


# ---------------------------------------------------------- CLEARED TRAINING DATASET CREATED! --------------------------------------------------------------------------------------



# ----------------------------------------------------------- XGB train, test and validation ----------------------------------------------------------------------------------------

# Step 1: Import the GeoDataFrame from the saved shapefile
reimported_gdf = gpd.GeoDataFrame.from_file(shapefile_path)

# Step 2: Load the descriptor variables folder and filter the folder to keep just the X most important ones:
predictors_path = r"predictors_path" # Workspace where the predictors .tif are stored. Notice that all predictors SHOULD HAVE same size (nº rows & columns)

    # Step 2.1: Create 'selected_predictors' folder in 'input_folder'
selected_predictors_folder = os.path.join(input_folder, "selected_predictors")
os.makedirs(selected_predictors_folder, exist_ok=True)

    # Step 2.2: Define a dictionary that maps the selected feature names to their corresponding file paths. Change names accordingly to match .tif names in 'predictors_path'
selected_features_files = {
    'dist_fresh': os.path.join(predictors_path, 'distance_to_freshwater_river_inputs_25830.tif'),
    'dist_OSM_c': os.path.join(predictors_path, 'distance_to_OSM_coastline_25830.tif'),
    'elev_MHT': os.path.join(predictors_path, 'elevation_related_to_MHW.tif'),
    'slope': os.path.join(predictors_path, 'slope_25830.tif'),
    'dist_MAT': os.path.join(predictors_path, 'distance_to_MAHT_countour_corrected.tif'),
    'dist_mshw': os.path.join(predictors_path, 'distance_to_MSHW_countour_corrected.tif'),
    'dist_MHW': os.path.join(predictors_path, 'distance_to_MHW_countour_corrected.tif'),
    'dist_MNHW': os.path.join(predictors_path, 'distance_to_MNHW_countour_corrected.tif'),
    'dist_MSL': os.path.join(predictors_path, 'distance_to_MSL_countour_corrected.tif')  
}

# Step 3: Use the selected feature names from RFECV to copy the corresponding predictor raster files and create an array with the predictor raster paths in order of importance:
raster_predictors = []

for feature in selected_features:
    file_path = selected_features_files.get(feature)  # Get the file path from the selected_features_files dictionary
    if file_path is not None:  # Check if the file path exists in the dictionary
        shutil.copy(file_path, os.path.join(selected_predictors_folder, os.path.basename(file_path)))
        raster_predictors.append(os.path.join(selected_predictors_folder, os.path.basename(file_path)))

    # Print the number of raster predictors:
print("{} raster predictors will be used in the computation".format(len(raster_predictors)))
print(raster_predictors)

# Step 4: Prepare the pyimpute workflow:
print("Preparing pyimpute workflow...")
# Load training vector
train_xs, train_y = load_training_vector(reimported_gdf, raster_predictors, response_field='class')
target_xs, raster_info = load_targets(raster_predictors)
train_xs.shape, train_y.shape
print("Pyimpute workflow prepared!")

# Step 5: Implement the scikit-learn classifiers:
CLASS_MAP = {
    'xgbc': {
        'model': OneVsOneClassifier(XGBClassifier(), n_jobs=-1),
        'params': {
            'learning_rate': sp_randFloat(),
            'subsample': sp_randFloat(),
            'n_estimators': sp_randInt(100, 300),   # Define the range where RandomSearch will search for the best hyperparameter value
            'max_depth': sp_randInt(2, 6)   # Define the range of tree depth where RandomSearch will try to find the best hyperparameter value
        }
    }
}

# Step 6: Lists to store results for XGBoost classifier
best_estimators = []

# Step 7: Implement Nested Cross Validation:
for name, classifier_info in CLASS_MAP.items(): # Create a loop just in case you want to try more than 1 classifier.
    model = classifier_info['model']    # Pick model information
    params = classifier_info['params']  # Pick model parameters configuration

    # Scorer for multiclassification problem in an imbalanced dataset:
    scorer = make_scorer(roc_auc_score, needs_proba=True,  average='macro', multi_class='ovo')  # Define scorer strategy

    # Inner Loop of nested cross-validation:
    inner_cv = StratifiedKFold(n_splits=5, shuffle = True, random_state=42)

    # Outer Loop of nested cross-validation:
    outer_cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42)

    # Define RandomizedSearchCV with the classifier, parameter grid and inner CV:
    iter_number = 20    # Number of parameter settings that are sampled:
    search = RandomizedSearchCV(model.estimator, param_distributions=params, n_iter=iter_number, cv=inner_cv, scoring=scorer, refit=True, return_train_score=True)

    # Clean and Initialize a variable to store the Best Estimator:
    best_estimator = None
    
    # Perform Nested Cross-Validation:
    for train_outer, test_outer in outer_cv.split(train_xs, train_y):
        # Split data into train and test sets for the outer loop:
        X_train_outer, X_test_outer = train_xs[train_outer], train_xs[test_outer]
        y_train_outer, y_test_outer = train_y[train_outer], train_y[test_outer]

            # Give Weight to the classess: In this case we will give more weight to the Mudflat, Channel and Saltmarsh classess
            # as Upland Areas are less important in our case.
        class_weights = {0:10, 1:10, 2:1, 3:10} # Class codes and values. Each code refer to 1 habitat/category

        # Fit RandomizedSearchCV on the training data to find the best estimator:
        result = search.fit(X_train_outer, y_train_outer, sample_weight=[class_weights[label] for label in y_train_outer])

        # Get the best estimator found by RandomSearchCV:
        current_best_estimator = result.best_estimator_

        # If it's the first iteration or if the current best is better than the previous best, save it:
        if best_estimator is None or current_best_estimator.score(X_test_outer, y_test_outer) > best_estimator.score(X_test_outer, y_test_outer):
            best_estimator =  current_best_estimator           
    
    #Print the best estimator parameters:
    print("Best parameters:")
    print("Learning rate:", best_estimator.learning_rate)
    print("Subsample:", best_estimator.subsample)
    print("Number of Estimators:", best_estimator.n_estimators)
    print("Max Depth:", best_estimator.max_depth)

    # Step 8: Create a folder for each Classifier in the 'output_folder':
    ml_out_folder_path = os.path.join(output_folder, name + '_images')
    if os.path.isdir(ml_out_folder_path):
        shutil.rmtree(ml_out_folder_path)
    os.mkdir(ml_out_folder_path)

    # Step 9: Save the best_estimator (trained XGBClassifier) as a .joblib file (if needed):
    joblib.dump(best_estimator, os.path.join(output_folder, f"{name}_best_model_joblib.joblib"))

    # Step 10: Use the best_estimator to make predictions and save the results:
    impute(target_xs, best_estimator, raster_info, outdir=ml_out_folder_path, class_prob=True, certainty=True)

    # ------------------------------------------------------ XGBoost train, test and validation Done! --------------------------------------------------------------------------------


    # ---------------------------------------------- Now we compute the confussion matrices with the best estimator ------------------------------------------------------------------

    # Define variables for average classification report and confussion matrices:
    originalclass = []
    predictedclass = []
    confusion_matrices = []

    # Create a function to store the custom ROC AUC scorer:
    def custom_roc_auc_scorer(y_true, y_pred_probabilities):
        y_pred = np.argmax(y_pred_probabilities, axis=1)
        originalclass.extend(y_true)
        predictedclass.extend(y_pred)
        confusion_matrices.append(confusion_matrix(y_true, y_pred))
        return roc_auc_score(y_true, y_pred_probabilities, average='macro', multi_class='ovo')

    # Use it in cross-validation
    cross_val_scores = cross_val_score(best_estimator, train_xs, train_y, cv=outer_cv, scoring=make_scorer(custom_roc_auc_scorer, needs_proba=True))

    # Print cross validation scores and mean score:
    print(cross_val_scores)
    print(np.mean(cross_val_scores.tolist()))

    # After the nested cross-validation loop we create a classification report also:
    classification_report_str = classification_report(originalclass, predictedclass)

    # Convert the classification report string to a DataFrame
    classification_report_df = pd.read_fwf(io.StringIO(classification_report_str), index_col=0)

    # Save the classification report to a CSV file
    report_filename = os.path.join(output_folder, f'{name}_classification_report.csv')
    classification_report_df.to_csv(report_filename, index=False)

    # Calculate the average confusion matrix
    average_confusion_matrix = sum(confusion_matrices) / len(confusion_matrices)

    # Calculate row sums to normalize the confusion matrix
    row_sums = average_confusion_matrix.sum(axis=1, keepdims=True)

    # Normalize the confusion matrix to percentages
    normalized_confusion_matrix = (average_confusion_matrix / row_sums) * 100

    # Save the normalized confusion matrix to a PNG image
    confusion_matrix_filename = os.path.join(output_folder, f'{name}_average_confusion_matrix_percentages.png')

    # Plot the normalized confusion matrix as a heatmap with values in the cells
    plt.figure(figsize=(8, 6))
    sns.heatmap(normalized_confusion_matrix, annot=True, fmt='.2f', cmap='Blues', cbar=False)  # Use '.2f' to format as float with 2 decimal places
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Average Confusion Matrix (Percentages)')
    plt.savefig(confusion_matrix_filename, bbox_inches='tight')
    plt.close()

    #   -------------------------------------------------------------- MODEL METRICS COMPUTED! --------------------------------------------------------------------------------------