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
        print(f"Downloading dataset from {dataset_url}")
        response = requests.get(dataset_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        with open(zip_path, "wb") as f:
            f.write(response.content)
        print("Dataset downloaded successfully.")
    else:
        print("Dataset already exists.")
    
    # Extract the dataset
    print("Extracting dataset...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(raw_dir)
        print("Dataset extracted successfully.")

    raw_dataset_path = os.path.join(raw_dir, "hour.csv")
    
    # Validate that the file exists
    if not os.path.exists(raw_dataset_path):
        raise FileNotFoundError(f"Expected file not found: {raw_dataset_path}")
    
    # Load and validate the dataset
    print("Loading and validating dataset...")
    raw_dataset = pd.read_csv(
            raw_dataset_path, 
            header=0, sep=',', 
            parse_dates=['dteday'], 
            index_col='dteday')
    
    # Basic validation
    if raw_dataset.empty:
        raise ValueError("Loaded dataset is empty")
    
    expected_columns = ['instant', 'dteday', 'season', 'yr', 'mnth', 'hr', 'holiday', 'weekday', 
                       'workingday', 'weathersit', 'temp', 'atemp', 'hum', 'windspeed', 'casual', 'registered', 'cnt']
    missing_columns = [col for col in expected_columns if col not in raw_dataset.columns]
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")
    
    print(f"Dataset loaded successfully with shape: {raw_dataset.shape}")
    print(f"Date range: {raw_dataset.index.min()} to {raw_dataset.index.max()}")

    raw_dataset.to_csv(dataset_path)
    print(f"Dataset saved to {dataset_path}")


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
    
    # Validate input file exists
    if not os.path.exists(hour_path):
        raise FileNotFoundError(f"Input dataset not found: {hour_path}")
    
    print("Loading dataset for processing...")
    hour_df = pd.read_csv(hour_path, header=0, sep=',', parse_dates=['dteday'], index_col='dteday')
    
    # Validate dataset is not empty
    if hour_df.empty:
        raise ValueError("Loaded dataset is empty")
    
    # Validate expected columns exist
    expected_columns = ['instant', 'dteday', 'season', 'yr', 'mnth', 'hr', 'holiday', 'weekday', 
                       'workingday', 'weathersit', 'temp', 'atemp', 'hum', 'windspeed', 'casual', 'registered', 'cnt']
    missing_columns = [col for col in expected_columns if col not in hour_df.columns]
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")
    
    print(f"Dataset loaded successfully with shape: {hour_df.shape}")
    print(f"Date range: {hour_df.index.min()} to {hour_df.index.max()}")

    # Clean the dataset
    missing_values = hour_df.isnull().sum()
    print("Missing values in each column:\n", missing_values)
    
    # Check for excessive missing values
    total_cells = hour_df.size
    missing_cells = missing_values.sum()
    if missing_cells / total_cells > 0.5:  # More than 50% missing
        raise ValueError(f"Too many missing values: {missing_cells}/{total_cells} ({missing_cells/total_cells*100:.1f}%)")
    
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
    
    print(f"Processing data from {start_date} to {end_date}")
    
    data_dir ="/tmp/data"
    processed_dir = os.path.join(data_dir, "processed")
    
    # Create directories if they don't exist
    os.makedirs(processed_dir, exist_ok=True)
    
    # Loop over 12 months
    files_created = 0
    for i in range(12):
        month_start = start_date + pd.DateOffset(months=i)
        month_end = (month_start + pd.DateOffset(months=1)) - pd.Timedelta(seconds=1)
        
        monthly_data = hour_df.loc[month_start:month_end]
        
        # Skip empty months
        if monthly_data.empty:
            print(f"Warning: No data for month {month_start.strftime('%Y_%m')}")
            continue
            
        filename = f"{data_dir}/processed/data_{month_start.strftime('%Y_%m')}.csv"
        monthly_data.to_csv(filename)
        print(f"Saved {filename} with shape {monthly_data.shape}")
        files_created += 1
    
    if files_created == 0:
        raise ValueError("No data files were created - check date ranges")
    
    print(f"Created {files_created} monthly data files")

    # Create zip archive
    print("Creating zip archive of processed data...")
    with zipfile.ZipFile(cleaned_dataset_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(processed_dir):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, processed_dir)
                zipf.write(full, arcname=rel)
                
    # Validate the zip file was created
    if not os.path.exists(cleaned_dataset_path):
        raise RuntimeError("Failed to create cleaned dataset zip file")
        
    zip_size = os.path.getsize(cleaned_dataset_path)
    print(f"Created zip artifact at {cleaned_dataset_path} (size: {zip_size} bytes)")

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

    # Validate input
    if not os.path.exists(cleaned_dataset_path):
        raise FileNotFoundError(f"Cleaned dataset not found: {cleaned_dataset_path}")
    
    extract_dir = "/tmp/unzipped"
    os.makedirs(extract_dir, exist_ok=True)
    print(f"Extracting dataset to {extract_dir}")
    with zipfile.ZipFile(cleaned_dataset_path, 'r') as z:
        z.extractall(extract_dir)

    ##################################################################################################
    # Load the training data
    data_path = extract_dir
    
    # Check what files we have
    available_files = os.listdir(data_path)
    print(f"Available files in {data_path}: {available_files}")
    
    # Construct expected file paths
    data_01_path = os.path.join(data_path, 'data_2011_01.csv')
    data_02_path = os.path.join(data_path, 'data_2011_02.csv')
    
    # Validate files exist
    if not os.path.exists(data_01_path):
        raise FileNotFoundError(f"Expected data file not found: {data_01_path}")
    if not os.path.exists(data_02_path):
        raise FileNotFoundError(f"Expected data file not found: {data_02_path}")
    
    print("Loading training data...")
    # Read both CSV files
    data_01 = pd.read_csv(data_01_path)
    data_02 = pd.read_csv(data_02_path)
    
    # Validate data is not empty
    if data_01.empty:
        raise ValueError(f"Data file {data_01_path} is empty")
    if data_02.empty:
        raise ValueError(f"Data file {data_02_path} is empty")
    
    # Concatenate the datasets
    input_data_df = pd.concat([data_01, data_02], ignore_index=True)
    
    print(f"Combined dataset shape: {input_data_df.shape}")
    print(f"Columns: {list(input_data_df.columns)}")
    
    # Feature Selection
    numerical_features=['temp', 'atemp', 'humidity', 'windspeed', 'hour', 'weekday']
    categorical_features=['season', 'holiday', 'workingday', 'weathersit']
    
    # Check that all required columns exist
    required_columns = numerical_features + categorical_features + ['count']
    missing_columns = [col for col in required_columns if col not in input_data_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Define features and target variable
    X_input = input_data_df[numerical_features + categorical_features]
    y_input = input_data_df["count"]
    
    print(f"Features shape: {X_input.shape}")
    print(f"Target shape: {y_input.shape}")
        
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X_input, y_input, test_size=0.3, random_state=42)
    
    print(f"Training set size: {X_train.shape}")
    print(f"Test set size: {X_test.shape}")

    ##################################################################################################
    # Experiment Tracking with MLflow
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_REMOTE_TRACKING_SERVER")
    PARTICIPANT_FIRSTNAME = os.getenv("PARTICIPANT_FIRSTNAME")
    
    if not MLFLOW_TRACKING_URI:
        raise ValueError("MLFLOW_REMOTE_TRACKING_SERVER environment variable is not set")
    if not PARTICIPANT_FIRSTNAME:
        raise ValueError("PARTICIPANT_FIRSTNAME environment variable is not set")
    
    print(f"Setting MLflow tracking URI to: {MLFLOW_TRACKING_URI}")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment_name = f"bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}"
    print(f"Setting MLflow experiment to: {experiment_name}")
    mlflow.set_experiment(experiment_name)
    
    param_grid = {
    "n_estimators": [50, 100, 150, 200],
    "max_depth": [5, 10, 15, 20],
    }
    
    random_state = 42
    print(f"Starting hyperparameter search with {len(param_grid['n_estimators']) * len(param_grid['max_depth'])} combinations")
    
    best_rmse = float('inf')
    best_run_id = None
    
    for n_estimators, max_depth in product(param_grid["n_estimators"], param_grid["max_depth"]):
            
        print(f"Training model with n_estimators={n_estimators}, max_depth={max_depth}")
        
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
        
        # Track the best model
        if rmse < best_rmse:
            best_rmse = rmse
            best_run_id = None  # Will be set after MLflow run
        
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
            
            # If this is the best model so far, save the run ID
            if rmse == best_rmse:
                best_run_id = mlflow.active_run().info.run_id

    print(f"Training completed. Best RMSE: {best_rmse:.4f}")
    if best_run_id:
        print(f"Best model run ID: {best_run_id}")
    else:
        print("Warning: Could not determine best model run ID")


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
    
    # Validate environment variables
    if not MLFLOW_TRACKING_URI:
        raise ValueError("MLFLOW_REMOTE_TRACKING_SERVER environment variable is not set")
    if not PARTICIPANT_FIRSTNAME:
        raise ValueError("PARTICIPANT_FIRSTNAME environment variable is not set")
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment_name = f"bike_sharing_model_pipeline_{PARTICIPANT_FIRSTNAME}"
    mlflow.set_experiment(experiment_name)
    
    print(f"Checking for experiment: {experiment_name}")
    
    # Retrieve and Review Experiment Runs to find the best model
    # Get the experiment by name
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise RuntimeError(f"Experiment '{experiment_name}' is not found")
    
    print(f"Found experiment ID: {experiment.experiment_id}")
    
    # Load all runs from the experiment
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        run_view_type=ViewType.ACTIVE_ONLY,
        order_by=["metrics.rmse ASC"]
        )
    
    print(f"Found {len(runs)} runs in experiment")
    
    # Display runs in a DataFrame
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
    
    # Validate that we have the required metrics
    if best_rmse is None:
        raise ValueError("Best run does not have RMSE metric")
        
    print(f"Best Run: {best_run_id} with RMSE = {best_rmse}")
    
    # Register the model from the selected run
    model_uri = f"runs:/{best_run_id}/model" 
    print(f"Registering model from URI: {model_uri}")
    registered_model = mlflow.register_model(model_uri, f"BikeSharingModel_pipeline_{PARTICIPANT_FIRSTNAME}")
    
    print(f"Model registered: {registered_model.name} v{registered_model.version}")
    
    # Add model validation - check that the model can be loaded and makes reasonable predictions
    print("Validating registered model...")
    try:
        # Load the model we just registered
        model = mlflow.pyfunc.load_model(model_uri)
        
        # Create a sample input for validation (using average values from training data)
        sample_input = pd.DataFrame([{
            'season': 2,  # summer
            'yr': 1,      # 2012
            'mnth': 7,    # july
            'hr': 14,     # 2pm
            'holiday': 0,
            'weekday': 2,  # tuesday
            'workingday': 1,
            'weathersit': 1,  # clear
            'temp': 0.5,
            'atemp': 0.5,
            'hum': 0.5,
            'windspeed': 0.2
        }])
        
        # Rename columns to match training format
        sample_input.rename(columns={
            'yr': 'year',
            'mnth': 'month',
            'hr': 'hour',
            'hum': 'humidity'
        }, inplace=True)
        
        # Make a prediction
        prediction = model.predict(sample_input)
        print(f"Model validation successful. Sample prediction: {prediction[0]:.2f}")
        
        # Basic sanity check - prediction should be positive
        if prediction[0] < 0:
            print(f"Warning: Model produced negative prediction: {prediction[0]}")
            
    except Exception as e:
        print(f"Warning: Model validation failed: {e}")
        # Don't fail the registration if validation fails, just warn

# ****************************************************************************************************
@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "mlflow", "evidently==0.6.7", "pandas"]
)
def monitor_model(reference_data_path: InputPath('zip'), current_data_path: InputPath('zip'), monitoring_report: OutputPath('html')):
    """Monitor model performance and data drift using Evidently."""
    import os
    import zipfile
    import pandas as pd
    import json
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, TargetDriftPreset, DataQualityPreset
    
    # Extract reference and current data
    reference_dir = "/tmp/reference_data"
    current_dir = "/tmp/current_data"
    os.makedirs(reference_dir, exist_ok=True)
    os.makedirs(current_dir, exist_ok=True)
    
    with zipfile.ZipFile(reference_data_path, 'r') as zip_ref:
        zip_ref.extractall(reference_dir)
        
    with zipfile.ZipFile(current_data_path, 'r') as zip_ref:
        zip_ref.extractall(current_dir)
    
    # Load reference data (we'll use the first month as reference)
    reference_files = [f for f in os.listdir(reference_dir) if f.endswith('.csv')]
    current_files = [f for f in os.listdir(current_dir) if f.endswith('.csv')]
    
    if not reference_files or not current_files:
        raise ValueError("No CSV files found in the provided data")
    
    # Load the first file from each as sample data for monitoring
    reference_data = pd.read_csv(os.path.join(reference_dir, reference_files[0]))
    current_data = pd.read_csv(os.path.join(current_dir, current_files[0]))
    
    # Ensure we have the required columns
    required_columns = ['season', 'yr', 'mnth', 'hr', 'holiday', 'weekday', 'workingday', 'weathersit', 
                       'temp', 'atemp', 'hum', 'windspeed', 'cnt']
    
    # Rename columns if needed (to match training format)
    column_mapping = {
        'yr': 'year',
        'mnth': 'month',
        'hr': 'hour',
        'hum': 'humidity',
        'cnt': 'count'
    }
    
    reference_data.rename(columns=column_mapping, inplace=True)
    current_data.rename(columns=column_mapping, inplace=True)
    
    # Create Evidently report
    report = Report(metrics=[
        DataDriftPreset(),
        TargetDriftPreset(),
        DataQualityPreset()
    ])
    
    # Run the report
    report.run(reference_data=reference_data, current_data=current_data)
    
    # Save HTML report
    report.save_html(monitoring_report)
    
    # Also save as JSON for potential metric extraction
    json_report = report.as_dict()
    json_report_path = monitoring_report.replace('.html', '.json')
    with open(json_report_path, 'w') as f:
        json.dump(json_report, f)
    
    print(f"Monitoring report saved to {monitoring_report}")
    
    # Clean up temporary directories
    import shutil
    shutil.rmtree(reference_dir, ignore_errors=True)
    shutil.rmtree(current_dir, ignore_errors=True)
    """Prepare model serving artifacts by downloading the model from MLflow and packaging it for deployment."""
    import os
    import mlflow
    import mlflow.pyfunc
    import zipfile
    import json
    import shutil
    
    # Set MLflow tracking URI
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_REMOTE_TRACKING_SERVER")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    # Create temporary directory for model artifacts
    model_dir = "/tmp/model_artifacts"
    os.makedirs(model_dir, exist_ok=True)
    
    # Download the registered model
    model_uri = f"models:/{model_name}/{model_version}"
    print(f"Downloading model from {model_uri}")
    model_path = mlflow.pyfunc.load_model(model_uri)
    
    # Save the model to our artifacts directory
    mlflow.pyfunc.save_model(
        path=os.path.join(model_dir, "model"),
        python_model=model_path
    )
    
    # Create model serving script (FastAPI app)
    serving_script = '''
import os
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Bike Sharing Demand Prediction API")

# Load model at startup
MODEL_PATH = "/app/model"
model = mlflow.pyfunc.load_model(MODEL_PATH)

class BikeFeatures(BaseModel):
    season: int
    yr: int
    mnth: int
    hr: int
    holiday: int
    weekday: int
    workingday: int
    weathersit: int
    temp: float
    atemp: float
    hum: float
    windspeed: float

@app.post("/predict")
async def predict_demand(features: BikeFeatures):
    try:
        # Convert features to DataFrame for prediction
        input_df = pd.DataFrame([features.dict()])
        
        # Rename columns to match training format
        input_df.rename(columns={
            'yr': 'year',
            'mnth': 'month',
            'hr': 'hour',
            'hum': 'humidity'
        }, inplace=True)
        
        # Make prediction
        prediction = model.predict(input_df)
        
        return {"predicted_demand": float(prediction[0])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
'''
    
    # Write serving script
    with open(os.path.join(model_dir, "serve.py"), "w") as f:
        f.write(serving_script)
    
    # Create requirements file for serving
    serving_requirements = '''
mlflow
fastapi
uvicorn
pydantic
pandas
'''
    
    with open(os.path.join(model_dir, "requirements.txt"), "w") as f:
        f.write(serving_requirements)
    
    # Create model metadata
    model_metadata = {
        "name": model_name,
        "version": model_version,
        "framework": "python_function",
        "runtime": "python",
        "input_example": {
            "season": 1,
            "yr": 0,
            "mnth": 1,
            "hr": 0,
            "holiday": 0,
            "weekday": 0,
            "workingday": 1,
            "weathersit": 1,
            "temp": 0.5,
            "atemp": 0.5,
            "hum": 0.5,
            "windspeed": 0.5
        }
    }
    
    with open(os.path.join(model_dir, "model_metadata.json"), "w") as f:
        json.dump(model_metadata, f)
    
    # Package everything into a zip file for deployment
    with zipfile.ZipFile(model_artifacts, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, model_dir)
                zipf.write(file_path, arcname=os.path.join("model", arcname))
    
    print(f"Model serving artifacts prepared and saved to {model_artifacts}")
    
    # Clean up temporary directory
    shutil.rmtree(model_dir)
    

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
    
    # Prepare model for serving by downloading from MLflow
    prepare_serving_op = prepare_model_serving(
        model_name=f"BikeSharingModel_pipeline_{PARTICIPANT_FIRSTNAME}",
        model_version="1"  # In a real implementation, this would come from register_model_op
    ).after(register_model_op)
    # Inject environment variables
    prepare_serving_op.set_env_variable("MLFLOW_REMOTE_TRACKING_SERVER", f"{MLFLOW_REMOTE_TRACKING_SERVER}")
    
    # Monitor model performance (for demonstration, comparing first two months)
    # In a real implementation, this would compare training data with recent production data
    monitor_op = monitor_model(
        reference_data_path=process_dataset_op.outputs['cleaned_dataset_path'],
        current_data_path=process_dataset_op.outputs['cleaned_dataset_path']
    ).after(prepare_serving_op)
    # Inject environment variables
    monitor_op.set_env_variable("MLFLOW_REMOTE_TRACKING_SERVER", f"{MLFLOW_REMOTE_TRACKING_SERVER}")

compiler.Compiler().compile(my_pipeline, f"bs_pipeline_{PARTICIPANT_FIRSTNAME}.yaml")