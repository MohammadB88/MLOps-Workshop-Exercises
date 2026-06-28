# 02_model_training_and_experiment_tracking.md

## Model Training and Experiment Tracking

This step focuses on automating the model selection process using a Random Forest Regressor and tracking experiments with MLflow.

### 1. Hyperparameter Tuning
The `train_model` component performs a grid search over the following parameters:
- `n_estimators`: [50, 100, 150, 200]
- `max_depth`: [5, 10, 15, 20]

### 2. MLflow Integration
For every combination of hyperparameters, the pipeline:
1. Trains a `RandomForestRegressor`.
2. Evaluates the model on a test set.
3. Logs the following to MLflow:
   - **Parameters**: `model_type`, `n_estimators`, `max_depth`, `random_state`.
   - **Metrics**: `rmse` (Root Mean Squared Error) and `r2` (R-squared score).
   - **Artifact**: The trained model object.

### 3. Identifying the Best Model
The component tracks the run with the lowest **RMSE**. This run ID is used in the subsequent registration step to ensure the best performing model is promoted to production.

### Key Concepts
- **Experiment Namespacing**: Experiments are named `bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}` to ensure individual workspaces.
- **Reproducibility**: By logging all parameters and metrics, we can reproduce the best model at any time.
