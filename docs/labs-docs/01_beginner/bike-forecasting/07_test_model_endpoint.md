# Exercise 7: Model Deployment - Testing Model Endpoint-API

## Objective
In this lab, we will:

* test the model endpoint-API by sending single and batch inference requests

ensuring the model can send back predictions based on the REST-API requests.

!!! tip "MLOps Perspective"
    Why this matters in an MLOps workflow: Testing endpoints ensures the deployed model serves predictions correctly.

## Prerequisites

- Completed Exercise 6
- Model deployed on OpenShift


## Step 1: Find and Open the Jupyter Notebook 

Please open the notebook, `"05_model_testing_endpoint.ipynb"` in the same directory ``"labs/01_beginner/bike_demand_forecasting"``.

## Step 2: Prepare or Find the Test Data
A sample test dataset (e.g., a few rows of processed features) is already created for you in CSV or txt format that matches the model's input schema: ``labs/01_beginner/bike_demand_forecasting/data/test_model``.

Run the cells in the notebook to take this test dataset and create the inference request.

## Step 3: Find Service URL for Model API on the OpenShift Console
Find your project (e.g. `user1`) in the openshift console.
💡 **Note:** Please make sure that you are in your given project.

This service url can be found under ``Networking -> Service -> bike-model-api-svc``. 
It is shown under the ``Hostname`` and end with ``svc.cluster.local``.

## Step 4: Set the Model Deployment Endpoint
In the notebook, the ``MODEL_API_SERVICE`` should be replaced with the service url, found in the last step. 

## Step 5: Simple and Batch Inferencing
As you follow the instruction in the notebook, single and batch requests are sent to the model endpoint.

The prediction is returned for all the test data and the comparison with the actual target values is shown.

Finally, a script is provided to visualize the ``Actual vs Predicted Counts`` for sample inputs.

## Summary

In this exercise, you:

1. Located the model API service URL on OpenShift
2. Set the model deployment endpoint in the notebook
3. Sent single and batch inference requests to the API
4. Visualized actual vs predicted values

---

