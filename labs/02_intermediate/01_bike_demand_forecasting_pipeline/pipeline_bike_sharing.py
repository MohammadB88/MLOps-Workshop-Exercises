from kfp import dsl, compiler
from kfp.dsl import InputPath, OutputPath

IMAGE_DATA_SCIENCE = "quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703"
PARTICIPANT_FIRSTNAME = "mohammad"
DATASET_URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
MLFLOW_REMOTE_TRACKING_SERVER = "http://mlflow-tracking.mlflow.svc.cluster.local:80"

# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
# def get_dataset(dataset_url: str) -> str:
def get_dataset(dataset_path: OutputPath('csv')):
    import os
    import zipfile
    import requests
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import json

    ##################################################################################################
    # Download and extract the bike sharing dataset from UCI Machine Learning Repository
    dataset_url = os.getenv("DATASET_URL")
    data_dir = "/tmp/data"
    raw_dir = os.path.join(data_dir, "raw")
    
    # Create directories if they don't exist
    os.makedirs(raw_dir, exist_ok=True)
    
    # Download the dataset
    zip_path = os.path.join(raw_dir, "bike_sharing_dataset.zip")
    if not os.path.exists(zip_path):
        response = requests.get(dataset_url)
        with open(zip_path, "wb") as f:
            f.write(response.content)
        print("Dataset downloaded success fully.")
    else:
        print("Dataset already exists.")
    
    # Extract the dataset
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(raw_dir)
        print("Dataset extracted successfully.")

    raw_dataset_path = os.path.join(raw_dir, "hour.csv")
    raw_dataset = pd.read_csv(
            raw_dataset_path, 
            header=0, sep=',', 
            parse_dates=['dteday'], 
            index_col='dteday')

    raw_dataset.to_csv(dataset_path)


# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def process_dataset(dataset_path: InputPath('csv'), cleaned_dataset_path: OutputPath('zip')):
    import os
    import zipfile
    import pandas as pd
    import matplotlib.pyplot as plt

    # Data Processing
    hour_path = dataset_path
    hour_df = pd.read_csv(hour_path, header=0, sep=',', parse_dates=['dteday'], index_col='dteday')
    
    # Clean the dataset
    missing_values = hour_df.isnull().sum()
    print("Missing values in each column:\n", missing_values)
    
    # Rename columns
    hour_df.rename(columns={
        'yr': 'year',
        'mnth': 'month',
        'hr': 'hour',
        'hum': 'humidity',
        'cnt': 'count'
    }, inplace=True)

    ##################################################################################################
    # Save the processed data to CSV files for each month
    start_date = hour_df.index.min().replace(day=1, hour=0, minute=0, second=0)
    end_date = hour_df.index.max()
    
    data_dir ="/tmp/data"
    processed_dir = os.path.join(data_dir, "processed")
    
    # Create directories if they don't exist
    os.makedirs(processed_dir, exist_ok=True)
    
    # Loop over 12 months
    for i in range(12):
        month_start = start_date + pd.DateOffset(months=i)
        month_end = (month_start + pd.DateOffset(months=1)) - pd.Timedelta(seconds=1)
        
        monthly_data = hour_df.loc[month_start:month_end]
        
        filename = f"{data_dir}/processed/data_{month_start.strftime('%Y_%m')}.csv"
        monthly_data.to_csv(filename)
        print(f"Saved {filename}")

    with zipfile.ZipFile(cleaned_dataset_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(processed_dir):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, processed_dir)
                zipf.write(full, arcname=rel)
                
    print("Created zip artifact at", cleaned_dataset_path)

# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "mlflow"]
    )
def train_model(cleaned_dataset_path: InputPath('zip')):
    import os
    import zipfile
    import random
    from itertools import product

    
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    
    import pandas as pd
    import numpy as np 
    
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
    from mlflow.entities import ViewType

    extract_dir = "/tmp/unzipped"
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(cleaned_dataset_path, 'r') as z:
        z.extractall(extract_dir)

    ##################################################################################################
    # Load the training data
    data_path = extract_dir
    
    # Read both CSV files
    data_01 = pd.read_csv(data_path + '/data_2011_01.csv')
    data_02 = pd.read_csv(data_path + '/data_2011_02.csv')
    
    # Concatenate the datasets
    input_data_df = pd.concat([data_01, data_02], ignore_index=True)
    
    input_data_df.head()
    
    # Feature Selection
    numerical_features=['temp', 'atemp', 'humidity', 'windspeed', 'hour', 'weekday']
    categorical_features=['season', 'holiday', 'workingday', 'weathersit']
    
    # Define features and target variable
    X_input = input_data_df[numerical_features + categorical_features]
    y_input = input_data_df["count"]
        
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X_input, y_input, test_size=0.3, random_state=42)

    ##################################################################################################
    # Experiment Tracking with MLflow
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_REMOTE_TRACKING_SERVER")
    PARTICIPANT_FIRSTNAME = os.getenv("PARTICIPANT_FIRSTNAME")
    mlflow.set_tracking_uri(f"{MLFLOW_TRACKING_URI}")
    mlflow.set_experiment(f"bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}")
    
    param_grid = {
    "n_estimators": [50, 100, 150, 200],
    "max_depth": [5, 10, 15, 20],
    }
    
    random_state = 42
    for n_estimators, max_depth in product(param_grid["n_estimators"], param_grid["max_depth"]):
            
        # Train a Regression Model
        model_randomforest = RandomForestRegressor(
            n_estimators=n_estimators, 
            max_depth=max_depth,
            random_state=random_state
            )
        model_randomforest.fit(X_train, y_train)
        
        # Predict on test set
        y_pred = model_randomforest.predict(X_test)
            
        ##################################################################################################
        # Model Evaluation Performance
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print(f"RMSE for {n_estimators} number of estimators: {rmse:.2f}")
        print(f"R² Score for {n_estimators} number of estimators: {r2:.2f}")
        
        random_num = random.randint(1000, 9999)  # generates a 4-digit random number
        
        run_name = f"RF_{n_estimators}_{max_depth}_{random_num}"
        print(f"This Run Name is {run_name}")
    
        with mlflow.start_run(run_name=run_name):
            mlflow.log_param("model_type", "RandomForest")
            mlflow.log_param("n_estimators", n_estimators)
            mlflow.log_param("max_depth", max_depth)
            mlflow.log_param("random_state", random_state)
        
            mlflow.log_metric("rmse", rmse)
            mlflow.log_metric("r2", r2)
        
            mlflow.sklearn.log_model(model_randomforest, "model")
            print("Model and metrics logged to MLflow.")


# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "mlflow"]
    )
def register_model():
    import os
    
    import pandas as pd
    
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.entities import ViewType

    ##################################################################################################
    # Set the MLflow tracking URI
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_REMOTE_TRACKING_SERVER")
    PARTICIPANT_FIRSTNAME = os.getenv("PARTICIPANT_FIRSTNAME")
    mlflow.set_tracking_uri(f"{MLFLOW_TRACKING_URI}")
    mlflow.set_experiment(f"bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}")
    
    # Retrieve and Review Experiment Runs to find the best model
    # Get the experiment by name
    experiment = mlflow.get_experiment_by_name(f"bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}")
    if experiment is None:
        raise RuntimeError(f"Experiment 'bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}' is not found")
    
    # Load all runs from the experiment
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        run_view_type=ViewType.ACTIVE_ONLY,
        order_by=["metrics.rmse ASC"]
        )
    
    print(runs)
    
    # Display runs in a DataFrame
    import pandas as pd
    
    df_runs = pd.DataFrame([{
        "Run ID": run.info.run_id,
        "Run Name": run.data.tags.get("mlflow.runName"),
        "RMSE": run.data.metrics.get("rmse"),
        "R2": run.data.metrics.get("r2"),
        "Date": run.info.start_time
    } for run in runs])
    
    df_runs.sort_values("R2", ascending=False).reset_index(drop=True)
 
    if not runs:
        raise RuntimeError("No Runs are found in the Experiment")
    
    # Select the Best Run (first item in the sorted list)
    best_run = runs[0]
    best_run_id = best_run.info.run_id
    best_rmse = best_run.data.metrics.get("rmse")
    
    print(f"Best Run: {best_run_id} with RMSE = {best_rmse}")

    # Register the model from the selected run
    model_uri = f"runs:/{best_run_id}/model" 
    registered_model = mlflow.register_model(model_uri, f"BikeSharingModel_pipeline_{PARTICIPANT_FIRSTNAME}")
    
    print(f"Model registered: {registered_model .name} v{registered_model .version}")

@dsl.pipeline(
    name=f'bs-pipeline_{PARTICIPANT_FIRSTNAME}',
    pipeline_root=f's3://runpipelines-{PARTICIPANT_FIRSTNAME}'
)
def my_pipeline():
    get_dataset_op = get_dataset()
    # Inject environment variables
    get_dataset_op.set_env_variable("DATASET_URL", f"{DATASET_URL}")
    
    process_dataset_op = process_dataset(dataset_path=get_dataset_op.outputs['dataset_path'])

    train_model_op = train_model(cleaned_dataset_path=process_dataset_op.outputs['cleaned_dataset_path'])
    # Inject environment variables
    train_model_op.set_env_variable("MLFLOW_REMOTE_TRACKING_SERVER", f"{MLFLOW_REMOTE_TRACKING_SERVER}")
    train_model_op.set_env_variable("PARTICIPANT_FIRSTNAME", f"{PARTICIPANT_FIRSTNAME}")
    
    register_model_op = register_model().after(train_model_op)
    # Inject environment variables
    register_model_op.set_env_variable("MLFLOW_REMOTE_TRACKING_SERVER", f"{MLFLOW_REMOTE_TRACKING_SERVER}")
    register_model_op.set_env_variable("PARTICIPANT_FIRSTNAME", f"{PARTICIPANT_FIRSTNAME}")

compiler.Compiler().compile(my_pipeline, f"bs_pipeline_{PARTICIPANT_FIRSTNAME}.yaml")