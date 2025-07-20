# Model Training & Experiment Tracking
In this task, you'll train a machine learning model using the prepared and split data. You'll also use an experiment tracking tool (e.g., MLflow) to log and compare key metrics such as accuracy, parameters, and model artifacts. This helps you keep track of different training runs and make informed decisions based on performance.

The steps in this task will be caried out in the second notebook: `02_model_training.ipynb`

💡 **Note:** Usually, the appropriate model is selected by data scientists based on the specific problem and data characteristics.  For the **bike sharing forecasting** problem, we will use the **`RandomForestRegressor`** model.

### 1. Set the MLflow Remote Tracking Server
**The link to the MLflow server will be provided during the workshop!**

You should replace the `MLFLOW_REMOTE_TRACKING_SERVER` with this provided URL.

### 2. Select Model Parameters
Choose model parameters (e.g., max_depth, n_estimators, learning_rate) from a predefined range:

``n_estimators``:  Number of decision trees that the model builds (i.e 50, 100, 200)

``max_depth``: Maximum depth of each tree (i.e 2, 6, 10, 15)

``random_state``: Ensures reproducibility of results by fixing the random seed. (i.e 42)

This allows you to experiment with different configurations.

### 3. MLflow UI - Compare Runs
Go to your MLflow UI to compare runs and evaluate model performance based on metrics and parameter choices.
