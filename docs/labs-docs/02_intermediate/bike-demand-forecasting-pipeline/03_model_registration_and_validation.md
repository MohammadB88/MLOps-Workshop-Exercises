# 03_model_registration_and_validation.md

## Model Registration and Validation

Once the best model is identified, it must be formally registered in the MLflow Model Registry to manage its lifecycle.

### 1. Selecting the Best Run
The `register_model` component:
- Queries the MLflow tracking server for all runs in the experiment.
- Sorts the runs by `rmse` in ascending order.
- Selects the run with the absolute minimum RMSE.

### 2. Model Registration
The model from the best run is registered as `BikeSharingModel_pipeline_{PARTICIPANT_FIRSTNAME}`. This assigns a version number to the model, allowing for easy rollbacks and version tracking.

### 3. Post-Registration Validation
To ensure the registered model is functional, the component performs a "sanity check":
- Loads the registered model using `mlflow.pyfunc.load_model`.
- Passes a sample input DataFrame.
- Verifies that the prediction is a positive number.

This step prevents "broken" models from progressing to the deployment stage.
