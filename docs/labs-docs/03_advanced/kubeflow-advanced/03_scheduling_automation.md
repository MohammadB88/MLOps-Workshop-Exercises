# Exercise 3: Scheduling & Automation

In this exercise, you will learn how to automate end-to-end ML workflows with production-grade scheduling, retraining logic, and version management.

## Learning Objectives

By the end of this exercise, you will be able to:
- Create recurring pipeline schedules with complex cron patterns
- Configure run triggers based on model performance thresholds
- Implement automated retraining logic with data drift detection
- Integrate pipelines with external monitoring systems
- Manage pipeline versions and implement rollback strategies

## Prerequisites

1. Completed Exercise 2: Advanced Workflows
2. Access to a Kubeflow Pipelines environment with persistent storage
3. MLflow tracking server configured for model registry

## Step 1: Creating Recurring Pipeline Schedules

KFP supports recurring runs with multiple scheduling options. Configure schedules with environment-specific parameters and timezone-aware cron expressions.

```python
import kfp
from kfp import dsl, Client
from datetime import timezone, timedelta

# Create a client
client = Client(host="http://localhost:8080")

# Define the pipeline with environment-aware configuration
@dsl.pipeline(
    name="bike-demand-retraining",
    description="Daily retraining pipeline with environment awareness",
)
def bike_demand_pipeline(
    dataset_path: str = "/data/bike_sharing.parquet",
    model_name: str = "bike-demand-model",
    environment: str = "staging",
    mlflow_tracking_uri: str = "http://mlflow:5000",
):
    # Pipeline components would be defined here
    pass


# Compile the pipeline
pipeline_func = bike_demand_pipeline
pipeline_package_path = "/tmp/bike_demand_pipeline.yaml"
kfp.compiler.Compiler().compile(
    pipeline_func=pipeline_func,
    package_path=pipeline_package_path,
)

# Create an experiment
experiment = client.create_experiment(
    name="bike-demand-production",
    description="Production pipeline for bike demand forecasting",
)

# Create a recurring run with timezone support
from datetime import datetime

recurring_run = client.create_recurring_run(
    experiment_id=experiment.experiment_id,
    job_name="bike-demand-daily-staging",
    pipeline_package_path=pipeline_package_path,
    cron_expression="0 6 * * *",          # Daily at 6 AM
    parameter_values={
        "dataset_path": "/data/bike_sharing.parquet",
        "model_name": "bike-demand-model",
        "environment": "staging",
    },
    enabled=True,
)

print(f"Scheduled job created: {recurring_run.job_id}")
print(f"Schedule: 0 6 * * * (daily at 6 AM)")

# Production schedule: hourly retraining during business hours
production_schedule = client.create_recurring_run(
    experiment_id=experiment.experiment_id,
    job_name="bike-demand-hourly-production",
    pipeline_package_path=pipeline_package_path,
    cron_expression="0 8-18 * * 1-5",     # Weekdays 8 AM - 6 PM
    parameter_values={
        "dataset_path": "/data/live/bike_sharing.parquet",
        "model_name": "bike-demand-model-prod",
        "environment": "production",
    },
    max_concurrency=1,                      # Prevent overlapping runs
    enabled=True,
)
```

## Step 2: Configuring Run Triggers with Performance Thresholds

Beyond time-based triggers, pipelines should only execute when conditions are met. Implement performance gates that decide whether to proceed with deployment.

```python
@dsl.component
def check_model_performance(
    model_uri: str,
    min_accuracy: float = 0.85,
) -> bool:
    """Evaluate a model's performance against a threshold."""
    import mlflow
    from mlflow.tracking import MlflowClient

    client = MlflowClient()

    # Load the latest model metrics
    model_version = client.get_latest_versions(
        name=model_uri, stages=["None", "Staging"]
    )

    if not model_version:
        print("No model version found")
        return False

    run_id = model_version[0].run_id
    run = client.get_run(run_id)
    accuracy = run.data.metrics.get("accuracy", 0)

    print(f"Model accuracy: {accuracy:.3f} (threshold: {min_accuracy})")
    return accuracy >= min_accuracy


@dsl.component
def check_data_drift(
    reference_data: str,
    current_data: str,
    drift_threshold: float = 0.3,
) -> bool:
    """Detect data drift between reference and current datasets."""
    import pandas as pd
    import numpy as np

    ref_df = pd.read_parquet(reference_data)
    cur_df = pd.read_parquet(current_data)

    # Simple drift detection using distribution comparison
    drift_scores = []
    for col in ref_df.select_dtypes(include=[np.number]).columns[:10]:
        ref_mean = ref_df[col].mean()
        cur_mean = cur_df[col].mean()
        ref_std = ref_df[col].std()

        if ref_std > 0:
            effect_size = abs(ref_mean - cur_mean) / ref_std
            drift_scores.append(effect_size)

    max_drift = max(drift_scores) if drift_scores else 0
    print(f"Max drift score: {max_drift:.3f} (threshold: {drift_threshold})")

    return max_drift < drift_threshold


@dsl.pipeline(name="threshold-gated-pipeline")
def threshold_gated_pipeline(
    model_name: str = "bike-demand-model",
    reference_data: str = "/data/reference.parquet",
    current_data: str = "/data/current.parquet",
):
    # Check both model performance and data drift
    perf_ok = check_model_performance(model_uri=model_name)
    drift_ok = check_data_drift(
        reference_data=reference_data,
        current_data=current_data,
    )

    # Only retrain if model is underperforming AND drift is detected
    with dsl.Condition(
        (perf_ok.output == False) & (drift_ok.output == False),
        name="needs-retraining",
    ):
        print("Performance degraded and drift detected — triggering retraining")
```

## Step 3: Implementing Automated Retraining Logic

Create a self-contained retraining pipeline that detects model degradation and triggers retraining automatically. This is a core MLOps pattern for keeping models current.

```python
@dsl.component
def should_retrain(
    model_name: str,
    performance_degradation_pct: float = 5.0,
) -> tuple:
    """Determine if model needs retraining based on performance metrics."""
    import mlflow
    from mlflow.tracking import MlflowClient

    client = MlflowClient()

    # Get performance from last N runs
    runs = client.search_runs(
        experiment_ids=["0"],
        filter_string=f"tags.mlflow.runName = '{model_name}'",
        max_results=10,
        order_by=["start_time DESC"],
    )

    if len(runs) < 2:
        print("Not enough runs to compare — skipping retraining check")
        return False

    latest = runs[0].data.metrics.get("accuracy", 0)
    previous = runs[1].data.metrics.get("accuracy", 0)

    if previous > 0:
        degradation = ((previous - latest) / previous) * 100
        print(f"Performance degradation: {degradation:.2f}%")
        print(f"Previous: {previous:.3f}, Latest: {latest:.3f}")

        if degradation >= performance_degradation_pct:
            print("Retraining threshold exceeded")
            return True

    return False


@dsl.component
def retrain_model(
    data_path: str,
    model_name: str,
    run_id: str,
) -> str:
    """Retrain the model using the latest data and log to MLflow."""
    import mlflow
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error

    mlflow.set_tracking_uri("http://mlflow:5000")

    with mlflow.start_run(run_name=f"retrain-{model_name}") as run:
        df = pd.read_parquet(data_path)
        X = df.drop("target", axis=1)
        y = df["target"]

        model = RandomForestRegressor(n_estimators=200)
        model.fit(X, y)

        predictions = model.predict(X)
        mse = mean_squared_error(y, predictions)
        mlflow.log_metric("mse", mse)
        mlflow.log_param("retrain_reason", "performance_degradation")

        model_uri = f"runs:/{run.info.run_id}/model"
        mlflow.register_model(model_uri, model_name)

        print(f"Model retrained and registered: {model_name}")
        return model_uri


@dsl.pipeline(name="automated-retraining")
def automated_retraining_pipeline(
    model_name: str = "bike-demand-model",
    data_path: str = "/data/latest.parquet",
):
    # Step 1: Decide if retraining is needed
    needs_retrain = should_retrain(model_name=model_name)

    # Step 2: Conditionally retrain
    with dsl.Condition(
        needs_retrain.output == True,
        name="perform-retraining",
    ):
        retrain_model(
            data_path=data_path,
            model_name=model_name,
            run_id="",
        )

    # Step 3: Always log the outcome
    print(f"Retraining decision: retrain={needs_retrain.output}")
```

## Step 4: Integrating with External Monitoring Systems

Connect KFP pipelines with external monitoring systems like Prometheus, Grafana, or alerting tools to enable automated incident response.

```python
@dsl.component(
    base_image="python:3.11",
    packages_to_install=["requests"],
)
def send_alert(
    alert_type: str,
    message: str,
    severity: str = "warning",
    webhook_url: str = "",
) -> bool:
    """Send an alert to a monitoring system via webhook."""
    import requests
    import json

    payload = {
        "alert_type": alert_type,
        "message": message,
        "severity": severity,
        "source": "kubeflow-pipeline",
    }

    if webhook_url:
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            print(f"Alert sent: {alert_type} ({severity})")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to send alert: {e}")
            return False

    print(f"Alert generated (no webhook): {message}")
    return True


@dsl.component(
    base_image="python:3.11",
    packages_to_install=["prometheus-client"],
)
def expose_metrics(
    pipeline_name: str,
    run_status: str,
    duration_seconds: float,
    model_accuracy: float = None,
) -> bool:
    """Expose pipeline metrics to Prometheus for monitoring."""
    from prometheus_client import Counter, Gauge, push_to_gateway

    # Define metrics
    run_counter = Counter(
        "pipeline_runs_total",
        "Total pipeline runs",
        ["pipeline_name", "status"],
    )
    duration_gauge = Gauge(
        "pipeline_duration_seconds",
        "Pipeline run duration",
        ["pipeline_name"],
    )

    # Push metrics to Prometheus pushgateway
    run_counter.labels(
        pipeline_name=pipeline_name,
        status=run_status,
    ).inc()

    duration_gauge.labels(
        pipeline_name=pipeline_name,
    ).set(duration_seconds)

    try:
        push_to_gateway(
            "prometheus-pushgateway:9091",
            job="kubeflow_pipelines",
            registry=run_counter.collect(),
        )
        print(f"Metrics pushed for {pipeline_name}")
        return True
    except Exception as e:
        print(f"Failed to push metrics: {e}")
        return False
```

Integration with Grafana for dashboards:

```json
{
  "dashboard": {
    "title": "ML Pipeline Health",
    "panels": [
      {
        "title": "Pipeline Run Status",
        "type": "stat",
        "targets": [
          {
            "expr": "pipeline_runs_total{status=\"Failed\"}",
            "legendFormat": "Failures"
          }
        ]
      },
      {
        "title": "Pipeline Duration",
        "type": "timeseries",
        "targets": [
          {
            "expr": "pipeline_duration_seconds",
            "legendFormat": "{{pipeline_name}}"
          }
        ]
      }
    ]
  }
}
```

## Step 5: Managing Pipeline Versions and Rollbacks

Version management is critical for production ML systems. KFP supports pipeline versioning and can integrate with MLflow's model registry for rollback capabilities.

```python
from kfp import Client
from datetime import datetime

client = Client(host="http://localhost:8080")


def upload_pipeline_version(
    pipeline_func,
    pipeline_name: str,
    version_tag: str,
):
    """Upload a new version of a pipeline."""
    package_path = f"/tmp/{pipeline_name}_{version_tag}.yaml"
    kfp.compiler.Compiler().compile(
        pipeline_func=pipeline_func,
        package_path=package_path,
    )

    # Upload new version
    pipeline = client.upload_pipeline_version(
        pipeline_package_path=package_path,
        pipeline_name=pipeline_name,
        pipeline_version_name=version_tag,
    )

    print(f"Uploaded {pipeline_name} version {version_tag}")
    return pipeline.id


def rollback_pipeline(
    pipeline_name: str,
    target_version: str,
):
    """Rollback a pipeline to a previous version."""
    pipeline = client.get_pipeline(name=pipeline_name)

    # List all versions
    versions = client.list_pipeline_versions(
        pipeline_id=pipeline.id,
        page_size=20,
    )

    # Find target version
    target = None
    for v in versions.versions:
        if v.name == target_version:
            target = v
            break

    if not target:
        print(f"Version {target_version} not found")
        return None

    # Create a recurring run using the old version
    new_job = client.create_recurring_run(
        experiment_id=client.create_experiment(
            name=f"rollback-{datetime.now().strftime('%Y%m%d')}"
        ).experiment_id,
        job_name=f"rollback-{pipeline_name}-{target_version}",
        pipeline_package_path=target.package_url,
        cron_expression="0 0 * * *",
        parameter_values={},
        enabled=True,
    )

    print(f"Rolled back to {target_version} — new job: {new_job.job_id}")
    return new_job


# Usage: version and rollback workflow
# Upload new version
# new_ver = upload_pipeline_version(
#     pipeline_func=bike_demand_pipeline,
#     pipeline_name="bike-demand-pipeline",
#     version_tag="v2.3.0",
# )

# Rollback if needed
# rollback_pipeline(
#     pipeline_name="bike-demand-pipeline",
#     target_version="v2.2.0",
# )


@dsl.component
def compare_and_promote(
    model_name: str,
    staging_threshold: float = 0.85,
    production_threshold: float = 0.90,
) -> str:
    """Compare model versions and promote if thresholds are met."""
    import mlflow
    from mlflow.tracking import MlflowClient

    client = MlflowClient()

    # Get latest versions in each stage
    staging_versions = client.get_latest_versions(
        model_name, stages=["Staging"]
    )
    production_versions = client.get_latest_versions(
        model_name, stages=["Production"]
    )

    if not staging_versions:
        print("No staging version found")
        return "no-action"

    staging_version = staging_versions[0]
    staging_run = client.get_run(staging_version.run_id)
    staging_acc = staging_run.data.metrics.get("accuracy", 0)

    print(f"Staging accuracy: {staging_acc:.3f}")

    # Promote to production if threshold met
    if staging_acc >= production_threshold:
        client.transition_model_version_stage(
            name=model_name,
            version=staging_version.version,
            stage="Production",
            archive_existing_versions=True,
        )
        print(f"Promoted version {staging_version.version} to Production")
        return "promoted"

    elif staging_acc >= staging_threshold:
        print(f"Version {staging_version.version} meets staging criteria")
        return "staging-only"

    print("Version does not meet any promotion criteria")
    return "rejected"
```

## Summary

In this exercise, you:
1. Created recurring pipeline schedules with timezone-aware cron expressions
2. Implemented performance-gated triggers that conditionally start pipelines
3. Built automated retraining logic triggered by model degradation
4. Integrated pipelines with Prometheus and webhook-based alerting systems
5. Established pipeline versioning and rollback procedures

---

<div style="display: flex; justify-content: space-between;">
<a href="../02_advanced_workflows/" class="md-button">← Previous</a>
<a href="../04_optimization_scaling/" class="md-button">Next →</a>
</div>
