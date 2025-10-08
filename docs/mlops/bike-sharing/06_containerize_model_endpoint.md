# 6: Model Deploymet - Containerize the Endpoint-API

## Objective
In this lab, we will:

* package the trained model into a RESTful API using a web framework (e.g., Flask or FastAPI) 
* containerize the service (e.g. with Docker, Podman, BuildConfig on OpenShift)

enabling easy deployment to cloud or on-prem environments and making the model accessible for real-time predictions via HTTP/S requests.

## Guide

### Step 1 - Review the REST API Application and Containerfile

REST-API application is written in python (`models/app.py`):

```python
# ./models/app.py
import os
import pandas as pd
import mlflow
from mlflow.pyfunc import PyFuncModel
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

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
```

Containerfile defines the logic to pack the model and REST-API application in a container image (`models/Containerfile`):
Take a note of the variables that should be set when deploying the application (i.e. **MLFLOW_TRACKING_URI**, **MODEL_NAME**. and **MODEL_VERSION**).

```bash
# ./models/Containerfile
FROM python:3.11-slim

# ── Install OS dependencies (optional but helpful) ───────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential         \
    && rm -rf /var/lib/apt/lists/*

# ── Set workdir and copy application code ────────────────────────────────
WORKDIR /app
COPY app.py ./

# ── Install Python requirements ──────────────────────────────────────────
# mlflow pulls in scikit-learn, pandas, etc.  --no-cache-dir keeps image small
RUN pip install --no-cache-dir fastapi uvicorn[standard] mlflow pandas pydantic

# ── Environment variables with sensible defaults (override at runtime) ──

# ── MLflow Tracking URI ────────────────────────────────────────────────
# This is the URI of the MLflow Tracking Server where the model is registered
# e.g. "https://mlflow_tracking_server.com"
ENV MLFLOW_TRACKING_URI=""

# ── Model name ───────────────────────────────────────────── 
# This is the name of the model registered in MLflow
# e.g. "BikeSharingModel"
ENV MODEL_NAME=""

# ── Model version ────────────────────────────────────────────
# This is the version of the model to load from MLflow.
# e.g. "1"
ENV MODEL_VERSION=""

# ── Entrypoint ───────────────────────────────────────────────────────────
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```


Now that we have an ``REST-API`` python application and a ``Containerfile``, we can build the container image for the model deployment.

### Step 2 - Go the to the OpenShift Console (Administrator Perspektive)
When logged in, go to the ``Administrator`` perspektive. You can find it by clicking on `Developer` at the top left corner.

Find your porject (e.g. `user1`) in the openshift console and click on it, so that the resources in this namespace will be shown. 

### Step 3 - Create an ImageStream on OpenShift
ImageStream on OpenShift is a container registery like ``hub.docker.com`` or `quay.io`, on which one can store and share images.

Go to `Buils -> ImageStream` to create an ImageStream on OpenShift to track and manage the container image built for your model API, allowing seamless integration with ``BuildConfig`` and deployments.

```bash
kind: ImageStream
apiVersion: image.openshift.io/v1
metadata:
  name: bike-sharing-imagestream
```

### 4. Create a BuildConfig on OpenShift
`BuildConfig` on OpenShift offers a way to build container images from Containerfiles and application sources that are stored on any git platform (i.e. `Github`). Since our code resides on Github, we use this method to build the image and will store it in the `ImageStream` created in the last step.

You can find this resource under `Buils -> BuildConfig`.

Click on create builconfig and go to the `yaml` view. You sould use these lines in the buildcondig page. 

💡 **Note:** **Copy the link to the forked repository and replace the `FORKED_REPO` before starting the build**.

```bash
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: bike-sharing-buildconfig
spec:
  source:
    type: Git
    git:
      uri: 'FORKED_REPO'
    contextDir: workshop_materials/bike_demand_forecasting/models
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Containerfile
      from:
        kind: DockerImage
        name: 'python:3.11-slim'
  output:
    to:
      kind: ImageStreamTag
      name: 'bike-sharing-imagestream:1.0'
```

This config tells OpenShift how to build the container image from your source code.

Now click on **Action** on top right corner and select **Start Build**. 

You can see the process of building the image in the respective builds-run under the tab `Builds`. 

When the `Status` is `Complete`, it means that the image is created and stored in the `ImageStream` you created in the last step.

Now if you go to the **ImageStream** (``bike-sharing-imagestream``), the built image is to be seen under `Tags`.

✅ **Next exercise** [Model Deploymet - Deploy on OpenShift Cluster](./07_model_deployment_openshift.md) **is about model deployment on the OpenShift Cluster.** 
