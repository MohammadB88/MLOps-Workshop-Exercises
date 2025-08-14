# Automating the Workflow with Kubeflow Pipelines
##### (Kubeflow Pipeline - Reading Data & Model Training, Tracking & Registering)

Using Kubeflow Pipelines, you'll automate the end-to-end workflow for reading data, training a model, tracking experiments, and registering the trained model. This ensures your ML process is reproducible and scalable, with automatic logging of parameters, metrics, and artifacts.

The steps in this task will be caried out in the directory `"workshop_materials/bike_demand_forecasting_pipeline"`.


### 1. Set the Variables for the Pipeline 

Update the python file (``pipeline_bike_sharing.py``) containing pipeline logic accordingly:  

- The image name for the pipeline (`IMAGE_FOR_PIPELINE`):
    ```bash
    quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703
    ```

- The link to the Dataset (`DATASET_URL`):
    ```bash
    https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip
    ```

- Set a dummy name or your firstname (it should be unique!)
💡 **Note One:** Letters should be all in lowercase 
💡 **Note Two:** There is only one instance of ``MLFlow server`` for all the participants. So in order to avoid any confusions, please make sure that you put an unique name!

You should replace the `YOUR_FIRSTNAME` with a dummy name or your firstname.


### 2. Convert the Pipeline from python to yaml format

RUN the pipeline

Look up the MLflow GUI and see the second registered model

Edit the deployment to load the second registered model

Just see the logs for the pod with which the new model is deployed.