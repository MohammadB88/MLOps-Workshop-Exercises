# 3: Model Training & Experiment Tracking

## Objective
In this lab, we will:

* Train some Models using the prepared ``Train`` and ``Test`` datasets
* Track the Experiments on MLflow

## Guide

### Step 1 - Find and Open the Jupyter Notebook 

In the same directory ``"workshop_materials/bike_demand_forecasting"``, you should open the notebook, `"03_model_training.ipynb"`.

### Step 2 - Load the Train and Test Data

In this task, we take the split dataset from the last task (`data/split`) and start with the model training.

### Step 3 - Set the MLflow Remote Tracking Server

💡 **Note:** **The link to the MLflow server will be provided during the workshop!**
You should replace the `MLFLOW_REMOTE_TRACKING_SERVER` with this provided URL.

### Step 4 - Set a Dummy Name or your Firstname (It should be unique!)

💡 **Note:** There is only one instance of ``MLflow Server`` for all the participants. So in order to avoid any confusion, please make sure that you put an unique name!

You should replace the `YOUR_FIRSTNAME` with a dummy name or your firstname.

### Step 5 - Select Model Parameters
Choose a set of the model parameters (e.g., max_depth, n_estimators) from a predefined range:

``N_ESTIMATORS``:  Number of decision trees that the model builds (i.e 50, 100, 200)

``MAX_DEPTH``: Maximum depth of each tree (i.e 2, 6, 10, 15)

<!-- ``random_state``: Ensures reproducibility of results by fixing the random seed. (It is set to 42. You should not change it!) -->

This allows you to experiment with different configurations.

### Step 6 - MLflow UI - Compare Runs in your specific Experiment
Go to your Experiment on ``MLflow UI`` to compare runs and evaluate model performance based on metrics and parameters.

💡 **Note:** Other participants are also storing their experiments on the same instance. So please make sure that you are in the correct experiment.

✅ **We will see in the next exercise** [Review the Experiments & Select the Best Model](./04_review_experiment_best_model.md), **how to select the best model and register that model on the same ``MLflow server``.**



<!-- # Model Training & Experiment Tracking
You'll also use an experiment tracking tool (e.g., *MLflow*) to log and compare key metrics such as accuracy (e.g. *rmse* and *r2*), parameters (e.g. *n_estimators* and *max_depth*), and model artifacts. This helps you keep track of different training runs and make informed decisions based on their performance.

💡 **Note:** Usually, the appropriate model is selected by data scientists based on the specific problem and characteristics of the data. For the **bike sharing forecasting** problem, we will use the ``"RandomForestRegressor"`` model and ``rmse`` and ``r2`` as deciding metrices. -->




