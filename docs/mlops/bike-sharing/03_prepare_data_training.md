# 3: Load, Extract, and Clean the Data

## Objective
In this lab, we will:

* Load the Processed Dataset
* Define Features and Target Variable
* Prepare the Data for Model Training

## Guide

### Step 1 - Find and Open the Jupyter Notebook 

In directory ``"workshop_materials/bike_demand_forecasting"``, please open the second notebook, `"02_model_training.ipynb"`, and follow the instructions below to complete this task.

### Step 2 - Load the Processed Data

In this task, we take the cleaned dataset from the last task (`data/processed`) and prepare it for model training.

Add the cleaned data for the first two month in the appropriate cell:
```bash
data_2011_01.csv
data_2011_02.csv
```

### step 3 - Set the Categorical Features

We already have set the numerical features. 

You only need to set these categorical features:
```bash
['season', 'holiday', 'workingday', 'weathersit']
```

### step 4 - Split the DataSet into Training and Test DataSets

In order to split the dataset into training and testing datasets, data scientists usually use ``train_test_split`` function from ``sklearn.model_selection`` module.

Just add this line of code in the appropriate cell, without any changes:
```bash
train_test_split(X_input, y_input, test_size=0.3, random_state=42)
```

### step 5 - Inspect the Split Data
Check the shape of your training and test datasets to confirm the split was successful:

Just paste this line in a cell under the same notebook and run it.
```bash
print(X_train.shape, X_test.shape)
```

(Optional) You can also print out the first 5 rows of both training and test data:

```bash
print(X_train.head(), X_test.head())
```

✅ **We use these ``Train`` and ``Test`` datasets to train a machine learning model in the next exercise** [Load, Extract, and Clean the Data](./03_model_training.md).