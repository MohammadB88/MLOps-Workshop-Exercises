# Model Deploymet - Containerize the Endpoint-API
In this task, you will package your trained model into a RESTful API using a web framework (e.g., Flask or FastAPI) and containerize the service (e.g. with Docker, Podman, BuildConfig on OpenShift). This makes the model accessible for real-time predictions via HTTP/S requests, enabling easy deployment to cloud or on-prem environments.

The steps in this task will be caried out in the third notebook: `"03_model_deployment.ipynb"`

### 1. Review the REST API App and Containerfile
- Inspect the `app.py` or main API script to understand the structure of the REST endpoint.
- Review the `Containerfile` (Dockerfile) to see how the application and model are packaged.
- Take a note of the variables that should be set by deployment.
  
### 2. Go the to the OpenShift Console
Find your porject (e.g. `user1`) in the openshift console.

### 3. Create an ImageStream on OpenShift
Go to `Buils -> ImageStream` to create an ImageStream on OpenShift to track and manage the container image built for your model API, allowing seamless integration with BuildConfig and deployments.

```bash
kind: ImageStream
apiVersion: image.openshift.io/v1
metadata:
  name: bike-sharing-imagestream
```

### 4. Create a BuildConfig on OpenShift
You can find this resource under `Buils -> BuildConfig`.

Click on create builconfig and go to the `yaml` view and paste these line there.
```bash
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: bike-sharing-buildconfig
spec:
  source:
    type: Git
    git:
      uri: 'https://github.com/FORK_REPO_PARTICIPATS/MLOps-Workshop-Exercises.git'
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

Now if you go to the **ImageStream** (``bike-sharing-imagestream``) you created in the last step, the built image is there.

In the next task, we take this image and deploy it on the OpenShift Cluster. 
