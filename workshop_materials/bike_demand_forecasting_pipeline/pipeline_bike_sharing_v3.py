from kfp import dsl, compiler
from kfp.dsl import InputPath, OutputPath

IMAGE_DATA_SCIENCE = "quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703"

# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
# def get_dataset(dataset_url: str) -> str:
def get_dataset(dataset_path: OutputPath('csv')):
    # Import necessary modules and libraries
    import os
    import zipfile
    import requests
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import json

    ##################################################################################################
    # Download and extract the bike sharing dataset from UCI Machine Learning Repository
    # This dataset contains hourly data of bike rentals in Washington, D.C. from 2011 to 2012
    # It includes features such as temperature, humidity, wind speed, and weather conditions.
    # Define URLs and paths
    dataset_url = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
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
    
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(dataset_path)
    print(raw_dataset.head())

    # return raw_dataset_path


# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def process_dataset(dataset_path: InputPath('csv'), cleaned_dataset_path: OutputPath('zip')):
    # Import necessary modules and libraries
    import os
    import zipfile
    import pandas as pd
    import matplotlib.pyplot as plt
    # import seaborn as sns
    # import json

    # Data Processing
    hour_path = dataset_path
    hour_df = pd.read_csv(hour_path, header=0, sep=',', parse_dates=['dteday'], index_col='dteday')
    
    # Display the first few rows
    # print('***************************************')
    # print('Output of this step!')
    # print('***************************************')
    # print(hour_df.head())
    
    # Clean the dataset
    # Convert categorical variables to appropriate types
    # Check for missing values
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
    # This will create a separate CSV file for each month in the dataset
    # Set the start date to the beginning of your data
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
        # zipdir(processed_dir, zipf)

        
    # monthly_data.to_csv(cleaned_dataset_path)
    
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(cleaned_dataset_path)
    print(monthly_data.head())


# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "mlflow"]
    )
def train_model(cleaned_dataset_path: InputPath('zip')):
    import os
    import zipfile
    import random
    
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
    # data_03 = pd.read_csv(data_path + 'data_2011_03.csv')
    
    # Concatenate the datasets
    # input_data_df = pd.concat([data_01, data_02, data_03], ignore_index=True)
    input_data_df = pd.concat([data_01, data_02], ignore_index=True)
    
    input_data_df.head()
    
    # Feature Selection
    # Set the type of features
    numerical_features=['temp', 'atemp', 'humidity', 'windspeed', 'hour', 'weekday']
    categorical_features=['season', 'holiday', 'workingday', 'weathersit']
    
    # Define features and target variable
    X_input = input_data_df[numerical_features + categorical_features]
    y_input = input_data_df["count"]
    
    # X_train.head()
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X_input, y_input, test_size=0.3, random_state=42)

    ##################################################################################################
    # Train a Regression Model
    # ``n_estimators``:  Number of decision trees that the model builds (i.e 50, 100, 200)
    #``max_depth``: Maximum depth of each tree (i.e 2, 6, 10, 15)
    #``random_state``: Ensures reproducibility of results by fixing the random seed. (i.e 42)
    
    # Define and train model
    n_estimators = 100
    max_depth=10
    random_state = 42
    
    model_randomforest = RandomForestRegressor(
        n_estimators=n_estimators, 
        random_state=random_state,
        max_depth=max_depth
        )
    model_randomforest.fit(X_train, y_train)
    
    # Predict on test set
    y_pred = model_randomforest.predict(X_test)
    
    # print(y_pred)
    
    ##################################################################################################
    # Model Evaluation Performance
    #- **RMSE** (Root Mean Squared Error): Measures the average magnitude of prediction errors. Lower values indicate better model performance.
    #- **R² Score** (Coefficient of Determination): Indicates how well the model explains the variance in the target variable. A value closer to 1.0 means a better fit.
    
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"RMSE for {n_estimators} number of estimators: {rmse:.2f}")
    print(f"R² Score for {n_estimators} number of estimators: {r2:.2f}")

    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(rmse, r2)
    print(cleaned_dataset_path)
    # print(cleaned_dataset.head())

    ##################################################################################################
    # Experiment Tracking with MLflow
    # Set the MLflow tracking URI
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_REMOTE_TRACKING_SERVER")
    mlflow.set_tracking_uri(f"{MLFLOW_TRACKING_URI}")
    mlflow.set_experiment("bike_sharing_model")
    
    random_num = random.randint(1000, 9999)  # generates a 4-digit random number
    run_name = f"random_forest_baseline_{n_estimators}_{random_num}"
    
    print(f"MLflow run name based on the number of estimators: {run_name}")
    
    # directory_path = "../model"
    # os.makedirs(directory_path, exist_ok=True)
    
    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_param("n_estimators", n_estimators)
    
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
    ##################################################################################################
    # Set the MLflow tracking URI
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_REMOTE_TRACKING_SERVER")
    mlflow.set_tracking_uri(f"{MLFLOW_TRACKING_URI}")
    mlflow.set_experiment("bike_sharing_model")
    
    # Retrieve and Review Experiment Runs to find the best model
    # Get the experiment by name
    experiment = mlflow.get_experiment_by_name("bike_sharing_model")
    if experiment is None:
        raise RuntimeError("Experiment 'bike_sharing_model' is not found")
    
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
        raise RuntimeError("Keine Runs im Experiment gefunden")
    
    # Besten Run auswählen (erster Eintrag in der sortierten Liste)
    best_run = runs[0]
    best_run_id = best_run.info.run_id
    best_rmse = best_run.data.metrics.get("rmse")
    
    print(f"👑 Bester Run: {best_run_id} mit RMSE = {best_rmse}")


@dsl.pipeline(
    name='bs-pipeline',
    pipeline_root='s3://runpipelines'
)
def my_pipeline():
    get_dataset_op = get_dataset()
    
    process_dataset_op = process_dataset(dataset_path=get_dataset_op.outputs['dataset_path'])
    
    train_model_op = train_model(cleaned_dataset_path=process_dataset_op.outputs['cleaned_dataset_path'])

    # Inject environment variables
    train_model_op.set_env_variable("MLFLOW_REMOTE_TRACKING_SERVER", "http://mlflow-tracking.mlflow.svc.cluster.local:80")

    register_model_op = register_model()
    register_model_op.set_env_variable("MLFLOW_REMOTE_TRACKING_SERVER", "http://mlflow-tracking.mlflow.svc.cluster.local:80")

compiler.Compiler().compile(my_pipeline, "bs_pipeline.yaml")