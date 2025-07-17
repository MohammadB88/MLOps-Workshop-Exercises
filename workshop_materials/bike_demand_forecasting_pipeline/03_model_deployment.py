# Import necessary modules
import os
import joblib

import requests
import json

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

import pandas as pd
import numpy as np

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient


##################################################################################################
# Select and Load the trained model
# The Model is trained in the previous step and saved in the MLflow tracking server.

# Initialize MLflow client
MLFLOW_TRACKING_URI = 'MLFLOW_REMOTE_TRACKING_SERVER'
mlflow.set_tracking_uri(f"{MLFLOW_TRACKING_URI}")
client = MlflowClient()

model_name = "BikeSharingModel"

# List available versions
versions = client.search_model_versions(filter_string=f"name='{model_name}'", order_by=["version_number DESC"])

print("📦 Available versions for model:", model_name)
for v in versions:
    print(f"Version: {v.version}, Stage: {v.current_stage}, Status: {v.status}, Run ID: {v.run_id}")

# Ask the user to select a version
selected_version = input("Enter the version number you want to download: ").strip()

# Load the selected model version
model_uri = f"models:/{model_name}/{selected_version}"
model = mlflow.pyfunc.load_model(model_uri=model_uri)

print(f"✅ Model version {selected_version} loaded successfully from MLflow.")



##################################################################################################
# Test the loaded Model

# Prepare 5 samples as inference inputs
test_model_path = "./data/test_model/"

# Read sample input CSV file
sample_input = pd.read_csv(test_model_path + 'sample_input_data.csv')

# sample_input.to_dict(orient ='split')
sample_input.head()


# We define the sample inputs using the same numerical and categorical features 
# used for model training
numerical_features=['temp', 'atemp', 'humidity', 'windspeed', 'hour', 'weekday']
categorical_features=['season', 'holiday', 'workingday', 'weathersit']

sample_X_input = sample_input[numerical_features + categorical_features]
sample_y_input = sample_input["count"]

sample_X_input.head()