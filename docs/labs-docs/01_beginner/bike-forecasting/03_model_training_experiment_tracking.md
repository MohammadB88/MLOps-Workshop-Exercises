# Exercise 3: Model Training & Experiment Tracking

## Objective
In this lab, we will:

* Train some Models using the prepared ``Train`` and ``Test`` datasets
* Track the Experiments on MLflow

!!! info "What you will learn"
    - How to train a Random Forest regressor with hyperparameter tuning.
    - Using MLflow to log parameters, metrics, and model artifacts.
    - How to compare multiple runs to identify the optimal model configuration.

!!! tip "MLOps Perspective"
    Manual experimentation is the "enemy" of reproducibility. Tracking every run in MLflow separates ML engineering from haphazard experimentation, allowing teams to collaborate, audit, and revert to previous model versions with confidence. Experiment tracking is the heartbeat of the iterative ML process. Instead of manually recording results in a spreadsheet, we use tools like MLflow to create a systemic record of truth. This ensures that when we find a "best model," we know exactly which hyperparameters and dataset version produced it.

## Prerequisites

- Training/test datasets are prepared

## Step 1: Find and Open the Jupyter Notebook 

In the same directory ``"labs/01_beginner/bike_demand_forecasting"``, you should open the notebook, `"03_model_training.ipynb"`.

## Step 2: Load the Train and Test Data

In this task, we take the split dataset from the last task (`data/split`) and start with the model training.

## Step 3: Set the MLflow Remote Tracking Server

💡 **Note:** **The link to the MLflow server will be provided during the workshop!**
You should replace the `MLFLOW_REMOTE_TRACKING_SERVER` with this provided URL.

## Step 4: Set a Dummy Name or your Firstname (It should be unique!)

💡 **Note:** There is only one instance of ``MLflow Server`` for all the participants. So in order to avoid any confusion, please make sure that you put an unique name!

You should replace the `YOUR_FIRSTNAME` with a dummy name or your firstname.

## Step 5: Select Model Parameters
Choose a set of the model parameters (e.g., max_depth, n_estimators) from a predefined range:

``N_ESTIMATORS``:  Number of decision trees that the model builds (i.e 50, 100, 200)

``MAX_DEPTH``: Maximum depth of each tree (i.e 2, 6, 10, 15)

<!-- ``random_state``: Ensures reproducibility of results by fixing the random seed. (It is set to 42. You should not change it!) -->

This allows you to experiment with different configurations.

## Step 6: Log Model Metrics
In this step, you will log the model's performance metrics to MLflow.

Use the exact variable names from the previous cell that contain the calculated ``RMSE`` and ``R2`` values so they can be logged correctly.

## Step 7: MLflow UI - Compare Runs in your specific Experiment
Go to your Experiment on ``MLflow UI`` to compare runs and evaluate model performance based on metrics and parameters.

💡 **Note:** Other participants are also storing their experiments on the same instance. So please make sure that you are in the correct experiment.

## Summary

In this exercise, you:

1. Loaded the training and test datasets
2. Connected to the MLflow tracking server
3. Trained multiple models with different hyperparameters
4. Logged performance metrics (RMSE and R2) to MLflow
5. Tracked experiments and compared runs in MLflow UI

---

