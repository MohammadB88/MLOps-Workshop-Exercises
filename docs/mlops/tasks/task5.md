# Model Deploymet - Containerize the Endpoint-API
In this task, you will package your trained model into a RESTful API using a web framework (e.g., Flask or FastAPI) and containerize the service using Docker. This makes the model accessible for real-time predictions via HTTP requests, enabling easy deployment to cloud or on-prem environments.

The steps in this task will be caried out in the third notebook: `03_model_deployment.ipynb`

### 1. Review the REST API App and Containerfile
- Inspect the `app.py` or main API script to understand the structure of the REST endpoint.
- Review the `Containerfile` (Dockerfile) to see how the application and model are packaged.

### 2. Create an ImageStream on OpenShift
Create an ImageStream on OpenShift to track and manage the container image built for your model API, allowing seamless integration with BuildConfig and deployments.

```bash
kind: ImageStream
apiVersion: image.openshift.io/v1
metadata:
  name: bike-sharing-imagestream
  namespace: bike-sharing
```

### 3. Create a BuildConfig on OpenShift
Use the OpenShift Web Console or CLI (`oc`) to create a `BuildConfig`.
```bash
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  namespace: bike-sharing
  name: bike-sharing-buildconfig
spec:
  source:
    type: Git
    git:
      uri: 'https://github.com/MohammadB88/MLOps-Workshop-Exercises.git'
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
      namespace: 'bike-sharing'
      name: 'bike-sharing-imagestream:1.0'
```

This config tells OpenShift how to build the container image from your source code.

Now click on **Action** on top right corner and select **Start Build**. 

Now if you go to the **ImageStream** (``bike-sharing-imagestream``) you created in the last step, the built image is there.

In the next task, we take this image and deploy it on the OpenShift Cluster. 
