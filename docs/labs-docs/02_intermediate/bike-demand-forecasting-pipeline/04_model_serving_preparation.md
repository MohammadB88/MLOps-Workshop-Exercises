# 04_model_serving_preparation.md

## Model Serving Preparation

The goal of this step is to package the registered model and all its dependencies into a deployable artifact.

### 1. Artifact Collection
The `prepare_model_serving` component downloads the specific model version from the MLflow Model Registry.

### 2. Creating the Serving Application
The component dynamically generates a `serve.py` file using **FastAPI**. This application includes:
- `/predict`: A POST endpoint that accepts bike features and returns the predicted demand.
- `/health`: A GET endpoint for Kubernetes liveness/readiness probes.

### 3. Dependency Packaging
A `requirements.txt` file is created containing:
- `mlflow`
- `fastapi`
- `uvicorn`
- `pydantic`
- `pandas`

### 4. Final Artifact
All components (`model/` directory, `serve.py`, `requirements.txt`, and `model_metadata.json`) are bundled into a ZIP archive. This archive can be used by a CI/CD pipeline or a Kubernetes deployment to spin up a prediction service.
