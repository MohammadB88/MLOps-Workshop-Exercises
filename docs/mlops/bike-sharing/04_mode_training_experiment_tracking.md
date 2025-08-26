# 4: Model Training & Experiment Tracking

## Objective
In this lab, we will:

* Train some Models
* Track the Experiments

## Guide

The steps in this exercise will be carried out in the `"03_model_training.ipynb"` notebook.

# Model Training & Experiment Tracking
In this task, you'll train a machine learning model using the prepared ``Train`` and ``Test`` datasets in the last task. You'll also use an experiment tracking tool (e.g., *MLflow*) to log and compare key metrics such as accuracy (e.g. *rmse* and *r2*), parameters (e.g. *n_estimators* and *max_depth*), and model artifacts. This helps you keep track of different training runs and make informed decisions based on their performance.

The steps in this task will be caried out in the second notebook: `"02_model_training.ipynb"`

💡 **Note:** Usually, the appropriate model is selected by data scientists based on the specific problem and characteristics of the data. For the **bike sharing forecasting** problem, we will use the ``"RandomForestRegressor"`` model and ``rmse`` and ``r2`` as deciding metrices.

### 1. Set the MLflow Remote Tracking Server
💡 **Note:** **The link to the MLflow server will be provided during the workshop!**

You should replace the `MLFLOW_REMOTE_TRACKING_SERVER` with this provided URL.

### 2. Set a Dummy Name or your Firstname (It should be unique!)

💡 **Note:** There is only one instance of ``MLFlow server`` for all the participants. So in order to avoid any confusions, please make sure that you put an unique name!

You should replace the `YOUR_FIRSTNAME` with a dummy name or your firstname.

### 3. Select Model Parameters
Choose a set of the model parameters (e.g., max_depth, n_estimators) from a predefined range:

``n_estimators``:  Number of decision trees that the model builds (i.e 50, 100, 200)

``max_depth``: Maximum depth of each tree (i.e 2, 6, 10, 15)

``random_state``: Ensures reproducibility of results by fixing the random seed. (It is set to 42. You should not change it!)

This allows you to experiment with different configurations.

### 4. MLflow UI - Compare Runs
Go to your Experiment on ``MLflow UI`` to compare runs and evaluate model performance based on metrics and parameter choices.

💡 **Note:** Other participants are also storing their experiemnts on the same instance. So please make sure that you are in the correct experiment.

We will see in the next step how to select the best model and register that model on the same ``MLflow`` server it.