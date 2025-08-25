# ./models/app.py
import os
from fastapi import FastAPI, HTTPException
import pandas as pd
import mlflow
from mlflow.pyfunc import PyFuncModel

# ── 1. Read configuration from environment ──────────────────────────────
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI") # e.g. "https://mlflow_tracking_server.com"
MODEL_NAME = os.getenv("MODEL_NAME") or "BikeSharingModel"
MODEL_VERSION = os.getenv("MODEL_VERSION") # e.g. "5"  (optional)

if not MLFLOW_TRACKING_URI:
    raise RuntimeError("MLFLOW_TRACKING_URI environment variable not set")

if not MODEL_VERSION:
    raise RuntimeError("MODEL_VERSION environment variable not set!")

# ── 2. Connect to MLflow and load the model once at startup ─────────────
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# load a specific version
model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"

model: PyFuncModel = mlflow.pyfunc.load_model(model_uri)

# ── 3. API definition ───────────────────────────────────────────────────
app = FastAPI(title="Bike-Sharing Predictor",
              description=f"Served from {model_uri} at {MLFLOW_TRACKING_URI}",
              version="1.0.0")

# Health check model
class HealthCheck(BaseModel):
    status: str = "OK"

@app.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK,
         summary="Health check endpoint")
def health_check():
    return HealthCheck(status="OK")

@app.get("/", include_in_schema=False, summary="Root welcome or redirect")
def root():
    # Option A: friendly message
    return {"message": "Hello! Please try /docs to see the available endpoints."}

@app.post("/predict")
def predict(features: dict):
    """
    Accepts a JSON object of feature names / values
    and returns a single prediction.
    """
    try:
        df = pd.DataFrame([features])
        prediction = float(model.predict(df)[0])  # ensure JSON-serialisable
        return {"prediction": prediction}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
