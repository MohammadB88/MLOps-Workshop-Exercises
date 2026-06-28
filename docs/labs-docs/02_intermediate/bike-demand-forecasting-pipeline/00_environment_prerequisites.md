# 00_environment_prerequisites.md

## Environment Prerequisites

Before starting the Bike Demand Forecasting Pipeline lab, ensure your environment is correctly configured.

### 1. Required Software
- **Python 3.11+**
- **Kubeflow Pipelines (KFP) v2**
- **MLflow Tracking Server**
- **S3-compatible storage** (for pipeline artifacts)

### 2. Environment Variables
The pipeline relies on several environment variables for configuration. Ensure these are set in your pipeline runtime:

- `DATASET_URL`: The URL of the UCI bike sharing dataset.
- `MLFLOW_REMOTE_TRACKING_SERVER`: The URI of your MLflow tracking server (e.g., `http://mlflow-tracking.mlflow.svc.cluster.local:80`).
- `PARTICIPANT_FIRSTNAME`: Your first name, used to namespace experiments and avoid conflicts with other participants.

### 3. Dependencies
If you are performing local testing of components, install the required dependencies:

```bash
pip install -r labs/02_intermediate/bike_demand_forecasting_pipeline/requirements.txt
```
