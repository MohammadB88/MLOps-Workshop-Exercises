# 8: Model Deploymet - Testing Model Endpoint-API

## Objective
In this lab, we will:

* ???
ensuring your model is accessible and scalable in a production-like environment.

## Guide

### Step 1 - Go to the OpenShift Console
Find your porject (e.g. `user1`) in the openshift console.
💡 **Note:** Please make sure that you are in your given project.

### Step 5 - Prepare the Test Data
A sample test dataset (e.g., a few rows of processed features) is already created for you in CSV or txt format that matches the model’s input schema: ``workshop_materials/bike_demand_forecasting/data/test_model``.

Run the cells in the notebook to take this test dataset and create the inference request.

### 6. Set the Model Deployment Endpoint
In the notebook, the ``MODEL_API_SERVICE`` should be replaced with the service url we created in step 3. This url can be found, when going to the ``Networking -> Service -> bike-model-api-svc``. It is shown under the ``Hostname`` and end with ``svc.cluster.local``.

### 7. Simple and Batch Inferencing
As you follow the instruction in the notebook to send requests to test the model endpoint, you see that the prediction is returned for all the test data stored in the sample dataset.

Finally, a script is provided to visualize the ``Actual vs Predicted Counts`` for sample inputs.


✅ **Now with a model to deploy, we see how to prepare the deployment files and dependencies in a container, in the next exercise** [Model & Data Monitoring](./09_model_data_monitoring.md).


# Model Deploymet - 

We will test the deployment by sending a batch inferencing request using the Test Dataset to verify the model's functionality.
