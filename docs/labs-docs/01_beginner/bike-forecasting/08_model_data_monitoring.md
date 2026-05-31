# Exercise 8: Model & Data Monitoring

## Objective
In this lab, we will:

* implement basic monitoring to track the model’s performance and input data quality over time
* observe metrics such as data drift, model drift, target drift

ensuring the deployed model remains reliable and continues to perform well in a real-world environment.

!!! info "What you will learn"
    - The concept of Data, Target, and Model Drift in production ML.
    - How to use Evidently to generate monitoring reports.
    - How to compare baseline (reference) data against new (current) data to identify performance degradation.

!!! tip "MLOps Perspective"
    Why this matters in an MLOps workflow: Continuous monitoring detects data drift and model degradation in production.

## Prerequisites

- Completed Exercise 7
- Model endpoint accessible

## Step 1: Find and Open the Jupyter Notebook 

Please open the notebook, `"06_model_monitoring.ipynb"` in the same directory ``"labs/01_beginner/bike_demand_forecasting"``.


## Step 2: Find Service URL for Model API on the OpenShift Console
Find your project (e.g. `user1`) in the openshift console.
💡 **Note:** Please make sure that you are in your given project.

This service url can be found under ``Networking -> Service -> bike-model-api-svc``. 
It is shown under the ``Hostname`` and end with ``svc.cluster.local``.

## Step 3: Load the Processed Data

In this task, we need to set the path to the cleaned dataset (`data/processed`) as reference and current data.

``Reference data`` is the data the the model is trained on. 
``Current data`` is the unseen data to the model, which can be used to show the model performance over time. 

For reference data, you should set the first two month in the appropriate cell:
```bash
data_2011_01.csv
data_2011_02.csv
```

For current data, we set it for now to the third month in the appropriate cell:
```bash
data_2011_03.csv
```

Optional: You can try the whole notebook with data from another month to see the difference in the model performance. 

## Step 4: Add Predictions on Both Datasets as another Column
For this task, you do not need to change or add anything. Just run the corresponding cells.
These will get the predictions on both the reference and current datasets and add them as another column to the datasets, which is needed to generate monitoring reports in the next step.

## Step 5: Create and Observe the Drift Reports  
In order to generate different monitoring reports, we use ``Evidently`` as tool. 
As you execute the cells, observe how ``Evidently`` generate insights about the model and data, like data drift, model performance over time, and input data quality—all rendered interactively. I added a line to save this reports in ``html`` format under the directory ``reports/data_2011...``.

## Summary

In this exercise, you:

1. Set up model monitoring with Evidently
2. Created reference and current datasets for comparison
3. Generated drift reports to detect data and model drift
4. Interpreted monitoring results for production ML systems

---


