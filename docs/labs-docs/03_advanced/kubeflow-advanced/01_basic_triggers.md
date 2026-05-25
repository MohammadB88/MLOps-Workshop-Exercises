# Exercise 1: Basic Triggers

In this exercise, you will learn how to automate pipeline execution using time-based and event-based triggers in Kubeflow Pipelines.

## Learning Objectives

By the end of this exercise, you will be able to:
- Import the KFP SDK and configure a pipeline client
- Define reusable pipeline components
- Create cron-based recurring schedule triggers
- Configure event-based triggers for data-driven execution
- Monitor and manage triggered pipeline runs

## Prerequisites

1. Access to a Kubeflow Pipelines environment
2. Kubeflow Pipelines SDK installed (`pip install kfp`)
3. Basic understanding of Python decorators and type hints
4. Completed the beginner bike demand forecasting lab

!!! tip "MLOps Perspective"
    Production pipelines require sophisticated orchestration patterns. These skills enable scalable, reliable, and automated ML workflows.

## Step 1: Import KFP SDK and Configure the Client

The Kubeflow Pipelines SDK provides the `Client` class for interacting with the KFP API server. This is the entry point for creating experiments, running pipelines, and managing triggers.

```python
import kfp
from kfp import dsl
from kfp import client

# Configure the KFP client
# Point to your KFP instance (local, OpenShift, or cloud)
KFP_ENDPOINT = "http://localhost:8080"  # or your remote endpoint
client = kfp.Client(host=KFP_ENDPOINT)

# Verify connectivity
print(f"KFP version: {client.get_kfp_health().version}")
print(f"Experiments: {len(client.list_experiments().experiments)}")
```

## Step 2: Define a Simple Pipeline Component

Components are the building blocks of KFP pipelines. Each component is a self-contained step with inputs, outputs, and a containerized execution environment.

```python
from kfp.dsl import component, pipeline

@component(
    base_image="python:3.11",
    packages_to_install=["pandas", "scikit-learn"],
)
def load_and_validate_data(
    dataset_path: str,
    min_rows: int = 1000,
) -> str:
    """Load a dataset and validate it meets minimum size requirements."""
    import pandas as pd

    df = pd.read_csv(dataset_path)
    row_count = len(df)

    if row_count < min_rows:
        raise ValueError(
            f"Dataset has {row_count} rows, minimum {min_rows} required"
        )

    print(f"Loaded dataset with {row_count} rows, {len(df.columns)} columns")
    return dataset_path


@component(
    base_image="python:3.11",
    packages_to_install=["scikit-learn"],
)
def train_model(
    data_path: str,
    n_estimators: int = 100,
) -> str:
    """Train a Random Forest model and save it."""
    import pickle
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(n_estimators=n_estimators)
    # Model training logic here...
    model_path = "/tmp/model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    return model_path


@pipeline(name="simple-training-pipeline")
def training_pipeline(
    dataset_path: str = "/data/bike_sharing.csv",
    n_estimators: int = 100,
):
    load_task = load_and_validate_data(dataset_path=dataset_path)
    train_task = train_model(
        data_path=load_task.output,
        n_estimators=n_estimators,
    )
```

## Step 3: Create a Time-Based Trigger Using Cron Expressions

KFP supports recurring runs using standard cron expressions. This is useful for scheduled retraining or periodic data processing.

```python
import kfp
from kfp import dsl

# Define the pipeline reference
pipeline_ref = client.create_run_from_pipeline_func(
    training_pipeline,
    arguments={
        "dataset_path": "/data/bike_sharing.csv",
        "n_estimators": 200,
    },
)

# Create a recurring run using cron
# Every day at midnight
cron_expression = "0 0 * * *"

recurring_run = client.create_recurring_run(
    experiment_id=client.create_experiment(name="scheduled-training").experiment_id,
    job_name="daily-model-retraining",
    pipeline_package_path=pipeline_ref.pipeline_package_path,
    cron_expression=cron_expression,
    parameter_values={
        "dataset_path": "/data/bike_sharing.csv",
        "n_estimators": 200,
    },
)

print(f"Recurring run created: {recurring_run.job_id}")
print(f"Cron schedule: {cron_expression}")
```

Common cron patterns for MLOps workflows:

| Schedule     | Cron Expression    | Use Case                      |
|--------------|--------------------|-------------------------------|
| Hourly       | `0 * * * *`       | Real-time model updates       |
| Daily        | `0 0 * * *`       | Daily retraining              |
| Weekly       | `0 0 * * 0`       | Weekly evaluation             |
| Monthly      | `0 0 1 * *`       | Monthly model refresh         |

## Step 4: Configure an Event-Based Trigger for Data Arrival

Event-based triggers start pipeline execution when new data arrives. KFP can integrate with storage event systems to detect file creation or updates.

```python
from kfp.dsl import Dataset, Input, Output

@component(
    base_image="python:3.11",
    packages_to_install=["watchdog", "minio"],
)
def watch_for_new_data(
    bucket: str,
    prefix: str,
    poll_interval_seconds: int = 60,
) -> str:
    """Poll a storage bucket for new data files and trigger pipeline."""
    import time
    import os
    from minio import Minio

    # Configure MinIO client (S3-compatible storage)
    minio_client = Minio(
        endpoint=os.getenv("S3_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("S3_ACCESS_KEY", "minio"),
        secret_key=os.getenv("S3_SECRET_KEY", "minio123"),
        secure=False,
    )

    last_checked = time.time()

    # Check for new objects in the bucket
    objects = minio_client.list_objects(
        bucket, prefix=prefix, recursive=True
    )

    for obj in objects:
        obj_time = obj.last_modified.timestamp()
        if obj_time > last_checked:
            print(f"New data file detected: {obj.object_name}")
            return f"gs://{bucket}/{obj.object_name}"

    print("No new data files found")
    return None


# Usage with event-driven orchestration:
# kfp.Client().upload_pipeline_version(
#     pipeline_package_path=pipeline_file,
#     pipeline_name="event-driven-pipeline",
# )
```

For production, use KFP's built-in event trigger integration or configure webhooks via Argo Events:

```yaml
# event-based-trigger.yaml
apiVersion: argoproj.io/v1alpha1
kind: EventSource
metadata:
  name: data-arrival
spec:
  s3:
    data-bucket:
      endpoint: s3.amazonaws.com
      bucket:
        name: ml-data-bucket
      events:
        - s3:ObjectCreated:Put
      filter:
        prefix: incoming/
---
apiVersion: argoproj.io/v1alpha1
kind: Sensor
metadata:
  name: kfp-trigger
spec:
  dependencies:
    - name: new-data-dep
      eventSourceName: data-arrival
      eventName: data-bucket
  triggers:
    - template:
        name: kfp-workflow
        kfp:
          pipelineSpec:
            pipelineName: data-processing
            parameters:
              data_path: gs://ml-data-bucket/incoming/latest.csv
```

## Step 5: Run and Monitor Triggered Pipelines

Monitor pipeline executions using the KFP SDK and review run metadata to ensure triggers are operating correctly.

```python
import time
from kfp import Client

# Configure the client
client = Client(host=KFP_ENDPOINT)

# List recent runs
runs = client.list_runs(
    experiment_name="scheduled-training",
    page_size=10,
    sort_by="created_at desc",
)

print("Recent pipeline runs:")
for run in runs.runs:
    status = "Succeeded" if run.run.status == "Succeeded" else f"Failed: {run.run.error}"
    print(f"  - {run.run.name}: {status}")
    print(f"    Created: {run.run.created_at}")

# Monitor a specific run
def wait_for_completion(run_id: str, poll_interval: int = 30):
    """Poll until a pipeline run completes."""
    while True:
        run_detail = client.get_run(run_id=run_id)
        status = run_detail.run.status
        print(f"Run status: {status}")

        if status in ["Succeeded", "Failed", "Skipped"]:
            return status

        time.sleep(poll_interval)


# Example: check trigger execution history
jobs = client.list_recurring_runs()
print(f"\nActive scheduled jobs: {len(jobs.jobs)}")
for job in jobs.jobs:
    print(f"  - {job.name}: {job.status}")
    print(f"    Cron: {job.cron_expression}")
    print(f"    Last run: {job.last_execution_time}")
```

## Summary

In this exercise, you:

1. Configured a KFP client and connected to a pipeline server
2. Defined reusable pipeline components for data validation and training
3. Created a cron-based recurring run for daily model retraining
4. Configured event-based triggers using S3 event detection
5. Monitored and inspected triggered pipeline executions

---

