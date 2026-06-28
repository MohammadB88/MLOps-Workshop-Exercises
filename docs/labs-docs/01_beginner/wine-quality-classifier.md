# Wine Quality Classifier

<figure markdown>
  ![wine quality logo](../assets/images/wine_quality_classiffier.png#only-light){ width="400" }
  ![wine qualita logo](../assets/images/wine_quality_classiffier.png#only-dark){ width="400" }
  <figcaption></figcaption>
</figure>


## Objective
In this exercise there are 4 steps from data to deployed model onto the OpenShift cluster.
For each of these steps, a Jupyter Notebook is prepared.

## Prerequisites

- Access to an OpenShift AI JupyterLab environment
- Basic familiarity with Python and Jupyter notebooks

!!! tip "MLOps Perspective"
    This end-to-end exercise demonstrates the complete MLOps lifecycle — from data exploration through deployment and monitoring — showing how each stage connects in a production ML workflow.

### 1. Data Explorations and Processing
Inside the first notebook we read the input data and perform some data exploration tasks. After processing and cleaning the data, it will be stored in a processed dataset. 

Processed data will be then split into 3 datasets, *train_dataset*, *test_dataset*, and *performance_dataset* and stored in the corresponding directories. 

### 2. Model Training and registration as well as Experment tracking
We take the preprocessed data and start training a model. The trained model as well as its performance and artifacts can be tracked using **MLflow**. 

Usually, data scientists will not be satisfied with the first try. Hence, they will experiment with various sets of hyperparameters and different models. Next, these experiments will be compared on MLflow UI and the model with the best performance will be selected. 

curl -X GET 'https://{us-south.ml.cloud.ibm.com}/ml/v1/foundation_model_specs?version=2024-07-25&filters=function_embedding'


### 3. Local model deployment with the help of MLflow
This model can be deployed locally using 
```
mlflow models serve -m "models:/MODEL_NAME/MODEL_VERSION" --env-manager local --no-conda
```

But before starting the mlflow model server, the variable *MLFLOW_TRACKING_URI* should be defined:
```
export MLFLOW_TRACKING_URI=http://mlflow-mlflow.apps.cluster-db46l.dynamic.redhatworkshops.io
```


### 4. Model packaging and deployment on the OpenShift cluster
Now that the model and its dependencies are pushed to the Github repository, we are ready to go to the OpenShift cluster and start building a container image for the model and deploying it on the cluster. finally we use the deployed model API to send prediction requests using a frontend application.

<figure markdown>
  ![CC Logo](../assets/images/steps-openshift.png#only-light){ width="500" }
  ![CC Logo](../assets/images/steps-openshift.png#only-dark){ width="500" }
  <figcaption></figcaption>
</figure>

There are two important hints:

* Take care of the specific permissions for images deployed on OpenShift cluster.

This line 
```
RUN chgrp -R 0 /opt && chmod -R g=u /opt
```
should be added to the *Dockerfile* After below line:
```
RUN chmod o+rwX /opt/mlflow/
```

* Configuring BuildConfig from Form is prone to error. So use the below template and adjust the corresponding variables.
```yaml title="BuildConfig" linenums="1" hl_lines="10-21"
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  namespace: BUILD_CONFIG_NAMESPACE
  name: BUILD_CONFIG_NAME
spec:
  source:
    type: Git
    git:
      uri: 'https://GIT_REPO_URL'
    contextDir: /GENERATE_DIRECTORY_CONTAINER_FILE
  strategy:
    type: Docker
    dockerStrategy:
      from:
        kind: DockerImage
        name: 'python:3.9.4-slim'
  output:
    to:
      kind: ImageStreamTag
      name: model-clf:1.0
```

As shown in the image, we should create an *ImageStream* resource and then a BuildConfig to configure the image building process.

When the container is running and the model API is ready, we can send a test requests as follows:

```py title="test model API" linenums="1" hl_lines="3"
# Send a prediction request to the deployed model on the OpenShift Cluster
BASE_URL = "http://model-clf-model-clf.apps.cluster-db46l.dynamic.redhatworkshops.io/"
endpoint = f"{BASE_URL}/invocations"
response = requests.post(endpoint, json=inference_request)

# Check if the response is successful
if response.status_code == 200:
    # Process the prediction response
    predictions = pd.DataFrame(response.json()['predictions'], columns=['Predicted Wine Quality'])

    # Combine predictions with actual classes
    actual_class_test = test_df_5['best quality'].reset_index(drop=True)
    model_output = pd.concat([predictions, actual_class_test], axis=1)

    # Rename columns for clarity
    model_output.columns = ['Predicted Wine Quality', 'Actual Wine Quality']

    # Display the final output
    print(model_output)
    
else:
    print(f"Request failed with status code: {response.status_code}")
    print(f"Response content: {response.text}")
```

### 5. Deploy the simple webapp
In order to consume the deployed model we will integrate it with a simple webapp. 
The code and Dockerfile for the app is in the same repository but in directory *app_wine_Clf*. 

We deploy the app in its own project. Let's call it *app-wine-clf*. Then create an imagestream and a buildconfig. 

<figure markdown>
  ![CC Logo](../assets/images/steps-openshift.png#only-light){ width="500" }
  ![CC Logo](../assets/images/steps-openshift.png#only-dark){ width="500" }
  <figcaption></figcaption>
</figure>

After the image is built, we can deploy the app. In the deployment definition we can set the model API by setting the variable **Endpoint_URL**. 

When the app is deployed and reachable through its route, we can test the model again but this time from a nice interface.


### 6. Model and Data Monitoring 

## Summary

In this lab, you:

1. Explored and processed the wine quality dataset
2. Trained a model with MLflow experiment tracking
3. Deployed the model locally using MLflow
4. Containerized and deployed the model on OpenShift
5. Integrated the model with a web application
6. Set up model monitoring

