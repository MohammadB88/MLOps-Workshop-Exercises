# Import necessary modules
import os
import zipfile

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

import pandas as pd
import numpy as np

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType

##################################################################################################
# Load the training data
data_path = "./data/processed/"

# Read both CSV files
data_01 = pd.read_csv(data_path + 'data_2011_01.csv')
data_02 = pd.read_csv(data_path + 'data_2011_02.csv')
# data_03 = pd.read_csv(data_path + 'data_2011_03.csv')

# Concatenate the datasets
# input_data_df = pd.concat([data_01, data_02, data_03], ignore_index=True)
input_data_df = pd.concat([data_01, data_02], ignore_index=True)

input_data_df.head()

# Feature Selection
# Set the type of features
numerical_features=['temp', 'atemp', 'humidity', 'windspeed', 'hour', 'weekday']
categorical_features=['season', 'holiday', 'workingday', 'weathersit']

# Define features and target variable
X_input = input_data_df[numerical_features + categorical_features]
y_input = input_data_df["count"]

# X_train.head()

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X_input, y_input, test_size=0.3, random_state=42)


##################################################################################################
# Train a Regression Model
# ``n_estimators``:  Number of decision trees that the model builds (i.e 50, 100, 200)
#``max_depth``: Maximum depth of each tree (i.e 2, 6, 10, 15)
#``random_state``: Ensures reproducibility of results by fixing the random seed. (i.e 42)

# Define and train model
n_estimators = 100
max_depth=10
random_state = 42

model_randomforest = RandomForestRegressor(
    n_estimators=n_estimators, 
    random_state=random_state,
    max_depth=max_depth
    )
model_randomforest.fit(X_train, y_train)

# Predict on test set
y_pred = model_randomforest.predict(X_test)

# print(y_pred)

##################################################################################################
# Model Evaluation Performance
#- **RMSE** (Root Mean Squared Error): Measures the average magnitude of prediction errors. Lower values indicate better model performance.
#- **R² Score** (Coefficient of Determination): Indicates how well the model explains the variance in the target variable. A value closer to 1.0 means a better fit.

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print(f"RMSE for {n_estimators} number of estimators: {rmse:.2f}")
print(f"R² Score for {n_estimators} number of estimators: {r2:.2f}")

##################################################################################################
# Experiment Tracking with MLflow
# Set the MLflow tracking URI
MLFLOW_TRACKING_URI = 'MLFLOW_REMOTE_TRACKING_SERVER'
mlflow.set_tracking_uri(f"{MLFLOW_TRACKING_URI}")
mlflow.set_experiment("bike_sharing_model")

random_num = random.randint(1000, 9999)  # generates a 4-digit random number
run_name = f"random_forest_baseline_{n_estimators}_{random_num}"

print(f"MLflow run name based on the number of estimators: {run_name}")

# directory_path = "../model"
# os.makedirs(directory_path, exist_ok=True)

with mlflow.start_run(run_name=run_name):
    mlflow.log_param("model_type", "RandomForest")
    mlflow.log_param("n_estimators", n_estimators)

    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("r2", r2)

    mlflow.sklearn.log_model(model_randomforest, "model")
    print("Model and metrics logged to MLflow.")

##################################################################################################
# Retrieve and Review Experiment Runs to find the best model
# Get the experiment by name
experiment = mlflow.get_experiment_by_name("bike_sharing_model")
if experiment is None:
    raise RuntimeError("Experiment 'bike_sharing_model' is not found")

# Load all runs from the experiment
client = mlflow.tracking.MlflowClient()
runs = client.search_runs(
    experiment_ids=[experiment.experiment_id],
    run_view_type=ViewType.ACTIVE_ONLY,
    order_by=["metrics.rmse ASC"]
    )

print(runs)

# Display runs in a DataFrame
import pandas as pd

df_runs = pd.DataFrame([{
    "Run ID": run.info.run_id,
    "Run Name": run.data.tags.get("mlflow.runName"),
    "RMSE": run.data.metrics.get("rmse"),
    "R2": run.data.metrics.get("r2"),
    "Date": run.info.start_time
} for run in runs])

df_runs.sort_values("R2", ascending=False).reset_index(drop=True)

if not runs:
    raise RuntimeError("Keine Runs im Experiment gefunden")

# Besten Run auswählen (erster Eintrag in der sortierten Liste)
best_run = runs[0]
best_run_id = best_run.info.run_id
best_rmse = best_run.data.metrics.get("rmse")

print(f"👑 Bester Run: {best_run_id} mit RMSE = {best_rmse}")

# # Ask user to select a run name
# selected_name = input("Enter the run name with the best performance to register its model: ")
# # Find the corresponding run ID
# selected_run = next(run for run in runs if run.data.tags.get("mlflow.runName") == selected_name)
# run_id = selected_run.info.run_id

# Register the model from the selected run
model_uri = f"runs:/{best_run_id}/model"
registered_model  = mlflow.register_model(model_uri, f"BikeSharingModel")

print(f"Model registered: {registered_model .name} v{registered_model .version}")