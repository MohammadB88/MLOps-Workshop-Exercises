from kfp import dsl, compiler
from kfp.dsl import InputPath, OutputPath

IMAGE_DATA_SCIENCE = "quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703"

@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def get_dataset(dataset_path: OutputPath('Dataset')):
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
    data_dir = "./data"
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

    dataset_path_file = f"{raw_dir}/hour.csv"
    dataset = pd.read_csv(dataset_path_file, header=0, sep=',', parse_dates=['dteday'], index_col='dteday')

    dataset.to_csv(dataset_path)
    
    # with open(dataset_path, 'w') as f:
    #     json.dump(dataset, f)
    
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(dataset_path)
        
    # dataset = {'my_dataset': [[1, 2, 3], [4, 5, 6]]}
    # with open(dataset_path, 'w') as f:
    #     json.dump(dataset, f)

@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def process_dataset(dataset_path: InputPath('Dataset'), cleaned_dataset_path: OutputPath('Dataset')):
    # Import necessary modules and libraries
    # import os
    # import zipfile
    # import requests
    # import pandas as pd
    # import matplotlib.pyplot as plt
    # import seaborn as sns
    # import json

    cleaned_dataset_path = dataset_path
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(cleaned_dataset_path)

    # Data Processing
    # hour_path = dataset_path
    # df = pd.read_csv(hour_path, header=0, sep=',', parse_dates=['dteday'], index_col='dteday')
    
    # # Display the first few rows
    # # df.head()
    
    # # Clean the dataset
    # # Convert categorical variables to appropriate types
    # # Check for missing values
    # missing_values = df.isnull().sum()
    # print("Missing values in each column:\n", missing_values)
    
    # # Rename columns
    # df.rename(columns={
    #     'yr': 'year',
    #     'mnth': 'month',
    #     'hr': 'hour',
    #     'hum': 'humidity',
    #     'cnt': 'count'
    # }, inplace=True)


@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def consume_dataset(dataset: InputPath('Dataset')):
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(dataset)

@dsl.pipeline(
    name='bs-pipeline',
    pipeline_root='s3://runpipelines'
)
def my_pipeline():
    get_dataset_op = get_dataset()
    process_dataset_op = process_dataset(dataset_path=get_dataset_op.outputs['dataset_path'])
    consume_dataset(dataset=process_dataset_op.outputs['cleaned_dataset_path'])


compiler.Compiler().compile(my_pipeline, "bs_pipeline.yaml")