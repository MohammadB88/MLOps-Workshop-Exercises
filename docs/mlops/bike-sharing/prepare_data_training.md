# 2 - Load, Extract, and Clean the Data

## Objective
In this lab, we will:

* Load the Processed Dataset
* Define Features and Target Variable

## Guide

The steps in this exercise will be carried out in the `"02_data_preparation.ipynb"` notebook.

### Step 1 - Load the Processed Data


In this task, we take the cleaned dataset from the last task and get it ready for model training.
For that, please open the second notebook, `"02_model_training.ipynb"`, and follow the instructions below to complete this task.

### 1. 
Add the cleaned data for the first two month in the appropriate cell:
```bash
data_2011_01.csv
data_2011_02.csv
```

### 2. Set the Categorical Features
We already have set the numerical features. 

You only need to set these categorical features:
```bash
['season', 'holiday', 'workingday', 'weathersit']
```

### 3. Split the DataSet into Training and Test DataSets
Use ``train_test_split`` function from ``sklearn.model_selection`` module.

Just add this line of code in the appropriate cell, without any changes:
```bash
train_test_split(X_input, y_input, test_size=0.3, random_state=42)
```

### 4. Inspect the Split Data
Check the shape of your training and test sets to confirm the split:

```bash
print(X_train.shape, X_test.shape)
```

(Optional) You can also print out the first 5 rows of both training and test data:

```bash
print(X_train.head(), X_test.head()))
```

Next, we use these ``Train`` and ``Test`` datasets to train a machine learning model.