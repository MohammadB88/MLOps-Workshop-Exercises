# 8: Model & Data Monitoring

## Objective
In this lab, we will:

* ???
ensuring your model is accessible and scalable in a production-like environment.

## Guide

### Step 1 -

# Model & Data Monitoring
In this task, you'll implement basic monitoring to track your model’s performance and input data quality over time. This includes observing metrics such as prediction accuracy, data drift, and request volume to ensure the deployed model remains reliable and continues to perform well in a real-world environment.

Here we will be working in the fourth notebook: `04_model_monitoring.ipynb`

Since many of the cells automatically load the reference and batch data, fit the Evidently reports, and visualize results directly in your Jupyter environment, your only tasks are to ``set the model endpoint`` and ``run the notebook`` from top to bottom without modification or additional assignments. As you execute, observe how Evidently surfaces insights like data drift, model performance over time, and input data quality—all rendered interactively. This end-to-end execution gives you hands-on exposure to model and data monitoring workflows using Evidently in a practical forecasting scenario.

### Set the Model Deployment Endpoint
In the notebook, the ``MODEL_API_SERVICE`` should be replaced with the service url we created in step 2. This url can be found, when going to the ``Networking -> Service -> bike-model-api-svc``. It is shown under the ``Hostname`` and end with ``svc.cluster.local``.

