from kfp import dsl, compiler
from kfp.dsl import InputPath, OutputPath

IMAGE_DATA_SCIENCE = "quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703"

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


@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def consume_dataset(cleaned_dataset_path: InputPath('zip')):
    import os
    import zipfile
    import pandas as pd

    # cleaned_dataset = pd.read_csv(cleaned_dataset_path)

    extract_dir = "/tmp/unzipped"
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(cleaned_dataset_path, 'r') as z:
        z.extractall(extract_dir)
    
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print("Unzipped contents:", os.listdir(extract_dir))
    print(cleaned_dataset_path)
    # print(cleaned_dataset.head())
    

@dsl.pipeline(
    name='bs-pipeline',
    pipeline_root='s3://runpipelines'
)
def my_pipeline():
    get_dataset_op = get_dataset()
    process_dataset_op = process_dataset(dataset_path=get_dataset_op.outputs['dataset_path'])
    consume_dataset(cleaned_dataset_path=process_dataset_op.outputs['cleaned_dataset_path'])


compiler.Compiler().compile(my_pipeline, "bs_pipeline.yaml")