# Exercise 1: Load, Extract, and Clean the Data

## Objective
In this lab, we will:

* Download and extract the Bike Sharing Dataset from the UCI Machine Learning Repository.
* Clean and prepare the data for analysis.
* Understand the data through visualization and summary statistics.
* Store the cleaned data for future use.
<!-- 1. **Load and Extract the Dataset**: 
2. **Perform Basic Data Preprocessing**: 
3. **Conduct Exploratory Data Analysis (EDA)**: 
4. **Save the Processed Data**:  -->

!!! info "What you will learn"
    - How to ingest raw datasets and perform initial cleaning.
    - Techniques for exploratory data analysis (EDA) to uncover patterns.
    - How to prepare a dataset for machine learning model training.

!!! tip "MLOps Perspective"
    Production-grade ML starts with data quality. In a real MLOps pipeline, manual data exploration is replaced by automated validation and preprocessing to ensure consistency and prevent 'garbage in, garbage out'. Standardizing how we explore and clean data allows us to build reproducible pipelines that can be versioned and audited—the foundation of the ML lifecycle.

## Prerequisites

- Repository cloned and opened

## Step 1: Find and Open the Jupyter Notebook 

In directory ``"labs/01_beginner/bike_demand_forecasting"``, look for notebook `"01_data_exploration.ipynb"` and open it. 

## Step 2: Download the dataset into the environment 

The Data for bike sharing company can be found under this link. 

```bash
https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip
```

You should set this URL at the beginning of the notebook for variable ``"DATASET_URL"`` (copy and paste the link).

Please follow the instructions inside the notebook and execute each code cell to explore, clean, and preprocess the dataset. The final cleaned dataset will be saved in the
`data/processed` directory.

## Summary

In this exercise, you:

1. Downloaded and extracted the Bike Sharing Dataset
2. Cleaned and preprocessed the data for analysis
3. Performed exploratory data analysis with visualizations
4. Saved the cleaned dataset for model training

---

