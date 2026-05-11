# Bike-Sharing Demand Forecasting Pipeline

<!-- ![docs\assets\images\bike_sharing_logo.png](docs\assets\images\bike_sharing_logo.png) -->

<figure markdown>
  ![bike sharing logo](../assets/images/bike_sharing_logo.png#only-light){ width="200" }
  ![bike sharing logo](../assets/images/bike_sharing_logo.png#only-dark){ width="200" }
  <figcaption></figcaption>
</figure>

## 🚲 Introduction

This lab builds upon the beginner bike-sharing demand forecasting exercise by implementing a complete MLOps pipeline using Kubeflow Pipelines. You will learn how to automate the entire machine learning lifecycle from data ingestion and preparation through model training, registration, serving, and monitoring.

The pipeline demonstrates key MLOps concepts including:
- Experiment tracking with MLflow
- Model reproducibility and versioning
- Automated model deployment preparation
- Foundation for model monitoring and drift detection

## Overview of the Pipeline

The pipeline consists of the following components:

1. **`get_dataset`**: Downloads and extracts the UCI bike sharing dataset
2. **`process_dataset`**: Cleans the data and splits it by month for distributed processing
3. **`train_model`**: Trains Random Forest models with hyperparameter tracking using MLflow
4. **`register_model`**: Registers the best performing model in the MLflow Model Registry
5. **`prepare_model_serving`**: Prepares model artifacts for deployment by downloading from MLflow

*Planned enhancements (to be implemented):*
6. **`serve_model`**: Deploy the model as a REST API service
7. **`monitor_model`**: Set up data drift and model performance monitoring

## Directory Structure

The bike_demand_forecasting_pipeline project is organized as follows:

```
bike_demand_forecasting_pipeline/
├── pipeline_bike_sharing.py      # Kubeflow pipeline definition
├── Containerfile                 # Dockerfile for model serving
├── requirements.txt              # Python dependencies
├── serve.py                      # FastAPI model serving application
├── k8s/                          # Kubernetes deployment manifests
│   ├── deployment.yaml           # Deployment configuration
│   └── service.yaml              # Service definition
└── data/                         # Sample data (for testing)
    ├── processed/                # Processed monthly datasets
    ├── raw/                      # Raw downloaded data
    └── test_model/               # Test data for model validation
```

## Component Details

### 1. Get Dataset Component
Downloads the bike sharing dataset from the UCI Machine Learning Repository and extracts it for processing. Includes validation checks for file existence, data integrity, and expected columns.

### 2. Process Dataset Component
Cleans the dataset by renaming columns for clarity and splits the data into monthly CSV files for easier distributed processing. Includes validation for input data, missing value checks, and verification of output files.

### 3. Train Model Component
Trains multiple Random Forest models with different hyperparameter combinations (n_estimators and max_depth). Each model configuration is tracked as an MLflow run with metrics (RMSE, R²) and parameters logged. Includes validation of input data, feature availability, and environment variables. Tracks the best model during training.

### 4. Register Model Component
Identifies the best model based on RMSE score from all training runs and registers it in the MLflow Model Registry. Includes validation of experiment existence, run data, and post-registration model validation with sample predictions.

### 5. Prepare Model Serving Component
Downloads the registered model from MLflow and packages it with a FastAPI serving script and dependencies for deployment.

### 6. Monitor Model Component
Uses Evidently to generate data drift, target drift, and data quality reports by comparing reference data (training data) with current data (production data). Saves HTML reports for visualization and JSON reports for metric extraction.

## Key Technologies

- **Kubeflow Pipelines**: Orchestration of ML workflow steps
- **MLflow**: Experiment tracking and model registry
- **FastAPI**: High-performance model serving API
- **scikit-learn**: Machine learning algorithms (Random Forest Regressor)
- **Evidently**: Model monitoring and drift detection (planned)
- **Docker/Kubernetes**: Containerization and orchestration (planned)

## Pipeline Variables

The pipeline uses the following environment variables that can be customized:

- `DATASET_URL`: URL to download the bike sharing dataset
- `MLFLOW_REMOTE_TRACKING_SERVER`: MLflow tracking server URI
- `PARTICIPANT_FIRSTNAME`: Used to namespace experiments and avoid conflicts

## How to Run the Pipeline

### Prerequisites
- Access to a Kubeflow Pipelines environment (e.g., OpenShift AI)
- MLflow tracking server accessible from the pipeline
- S3-compatible storage for pipeline artifacts

### Execution Steps
1. Ensure your environment variables are set correctly
2. Upload the `pipeline_bike_sharing.py` file to your Kubeflow Pipelines UI
3. Create an experiment or use an existing one
4. Create a pipeline run using the uploaded pipeline
5. Monitor the progress of each component through the UI

### Local Testing
For local development and testing:
```bash
# Install dependencies
pip install -r requirements.txt

# Run individual components for testing
python -c "
from pipeline_bike_sharing import get_dataset
import tempfile
import os

# Create temporary output path
with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
    get_dataset(dataset_path=tmp.name)
    print(f'Dataset saved to {tmp.name}')
"
```

## Expected Outputs

Each pipeline component produces specific outputs:

1. **get_dataset**: Raw hour.csv file
2. **process_dataset**: ZIP file containing monthly processed CSV files
3. **train_model**: MLflow runs with trained models and metrics
4. **register_model**: Registered model in MLflow Model Registry
5. **prepare_model_serving**: ZIP file containing model artifacts ready for deployment

## Connecting to Beginner Lab Concepts

This pipeline automates the manual steps you performed in the beginner lab:
- Data exploration and preparation → Automated in `get_dataset` and `process_dataset`
- Model training with hyperparameter tuning → Automated in `train_model`
- Model registration → Automated in `register_model`
- Model serving preparation → Automated in `prepare_model_serving`

The next steps would involve deploying the prepared model artifacts to a Kubernetes cluster and setting up monitoring, which are covered in the planned enhancements.

## Troubleshooting

Common issues and their solutions:

1. **MLflow connection errors**: Verify that `MLFLOW_REMOTE_TRACKING_SERVER` is set correctly and the server is accessible
2. **Dataset download failures**: Check network connectivity and the `DATASET_URL` variable
3. **Component failures**: Check the logs of each component in the Kubeflow Pipelines UI for detailed error messages
4. **Permission issues**: Ensure your service account has permissions to access the MLflow server and storage buckets

## Next Steps

To further enhance this pipeline, consider implementing:
1. Actual model deployment component that serves predictions via REST API
2. Model monitoring component that detects data and concept drift
3. Automated retraining triggers based on monitoring signals
4. A/B testing framework for model comparison
5. Integration with CI/CD pipelines for automated updates