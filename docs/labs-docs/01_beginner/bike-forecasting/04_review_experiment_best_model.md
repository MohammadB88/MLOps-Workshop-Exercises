# Exercise 4: Review the Experiments & Select the Best Model

## Objective
In this lab, we will:

* Review the performance of different models and runs
* Select the Model with the best performance

!!! tip "MLOps Perspective"
    Why this matters in an MLOps workflow: Model selection based on metrics is essential for deploying the best performing model.

## Prerequisites

- Completed Exercise 3
- MLflow experiments completed

## Step 1: Find and Open the Jupyter Notebook 

Please open the notebook, `"04_model_registration.ipynb"` in the same directory ``"labs/01_beginner/bike_demand_forecasting"``.


## Step 2: Set the MLflow Remote Tracking Server

💡 **Note:** **The link to the MLflow server will be provided during the workshop!**
You should replace the `MLFLOW_REMOTE_TRACKING_SERVER` with this provided URL.

## Step 3: Set a Dummy Name or your Firstname (It should be unique!)

💡 **Note:** There is only one instance of ``MLflow Server`` for all the participants. So in order to avoid any confusion, please make sure that you put an unique name!

You should replace the `YOUR_FIRSTNAME` with a dummy name or your firstname.

## Step 4: Review the Experiments' Results
At this step, you should just run the cell and review the output. 
Analyzing the results (i.e. comparing the metrics), you'll identify the best-performing model configuration and select it for further evaluation or deployment.

## Step 5: Select the Best-Performing experiment
When we prompted in the notebook, please select the run (``run-ID``) which has performed the best. 

## Summary

In this exercise, you:

1. Reviewed experiment results from MLflow
2. Compared model performance metrics
3. Selected the best-performing model run
4. Registered the best model in MLflow

---

