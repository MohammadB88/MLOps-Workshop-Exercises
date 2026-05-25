# Exercise 5: Monitoring & Debugging

In this exercise, you will learn how to monitor pipeline health, debug failures, and implement observability patterns for production Kubeflow Pipelines.

## Learning Objectives

By the end of this exercise, you will be able to:
- Add structured logging to pipeline components for observability
- Collect and expose custom metrics from pipeline runs
- Implement error handling and automated retry logic
- Debug failed pipeline runs using KFP's diagnostic tools
- Create monitoring dashboards for pipeline health and performance

## Prerequisites

1. Completed Exercise 4: Optimization & Scaling
2. Access to a KFP environment with persistent logging
3. Basic familiarity with Prometheus and Grafana concepts

!!! tip "MLOps Perspective"
    Production pipelines require sophisticated orchestration patterns. These skills enable scalable, reliable, and automated ML workflows.

## Step 1: Adding Structured Logging to Pipeline Components

Structured logging produces machine-parseable log output that can be indexed and searched. Use JSON-formatted logs for better integration with log aggregation systems like Elasticsearch or Loki.

```python
import json
import logging
import sys
from datetime import datetime, timezone
from kfp import dsl
from kfp.dsl import component


def setup_structured_logger(name: str) -> logging.Logger:
    """Configure a structured JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "logger": record.name,
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if hasattr(record, "extra_fields"):
                log_entry.update(record.extra_fields)
            return json.dumps(log_entry)

    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    return logger


@component(
    base_image="python:3.11",
    packages_to_install=["pandas", "scikit-learn"],
)
def logged_data_validation(
    data_path: str,
    expected_columns: list,
) -> dict:
    """Validate incoming data with structured logging."""
    import pandas as pd

    logger = setup_structured_logger("data_validation")
    logger.info("Starting data validation",
                extra={"extra_fields": {"data_path": data_path}})

    df = pd.read_csv(data_path)
    actual_columns = list(df.columns)

    missing_columns = set(expected_columns) - set(actual_columns)
    extra_columns = set(actual_columns) - set(expected_columns)

    report = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "missing_columns": list(missing_columns),
        "extra_columns": list(extra_columns),
        "null_counts": df.isnull().sum().to_dict(),
    }

    if missing_columns:
        logger.error("Missing required columns",
                     extra={"extra_fields": {
                         "missing": list(missing_columns),
                         "report": report,
                     }})
        raise ValueError(f"Missing columns: {missing_columns}")

    logger.info("Data validation passed",
                extra={"extra_fields": report})
    return report


@component
def logged_model_training(
    data_path: str,
    hyperparameters: dict,
) -> dict:
    """Train a model with structured logging of training metrics."""
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    import time

    logger = setup_structured_logger("model_training")
    logger.info("Starting model training",
                extra={"extra_fields": {
                    "data_path": data_path,
                    "hyperparameters": hyperparameters,
                }})

    df = pd.read_csv(data_path)
    X = df.drop("target", axis=1)
    y = df["target"]

    start_time = time.time()
    model = RandomForestRegressor(**hyperparameters)
    model.fit(X, y)
    training_time = time.time() - start_time

    predictions = model.predict(X)
    mse = mean_squared_error(y, predictions)
    r2 = r2_score(y, predictions)

    metrics = {
        "mse": mse,
        "r2": r2,
        "training_time_seconds": training_time,
        "n_estimators": hyperparameters.get("n_estimators"),
        "max_depth": hyperparameters.get("max_depth"),
    }

    logger.info("Training completed",
                extra={"extra_fields": {"metrics": metrics}})
    return metrics


@pipeline(name="logged-pipeline")
def logged_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    validation = logged_data_validation(
        data_path=data_path,
        expected_columns=["season", "holiday", "temp", "humidity", "count"],
    )
    training = logged_model_training(
        data_path=data_path,
        hyperparameters={"n_estimators": 200, "max_depth": 10},
    )
```

## Step 2: Collecting and Exposing Custom Metrics

Expose pipeline metrics for monitoring and alerting. Use MLflow for metrics logging and Prometheus for real-time observability.

```python
@component(
    base_image="python:3.11",
    packages_to_install=["mlflow", "scikit-learn", "prometheus-client"],
)
def collect_pipeline_metrics(
    model_metrics: dict,
    pipeline_name: str,
    run_id: str,
    mlflow_tracking_uri: str = "http://mlflow:5000",
) -> dict:
    """Log comprehensive metrics to MLflow and expose for Prometheus."""
    import mlflow
    from prometheus_client import Gauge, push_to_gateway
    import json

    # Log to MLflow
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    with mlflow.start_run(run_name=f"{pipeline_name}-{run_id}"):
        for metric_name, metric_value in model_metrics.items():
            if isinstance(metric_value, (int, float)):
                mlflow.log_metric(metric_name, metric_value)
                print(f"Logged metric: {metric_name}={metric_value}")

        mlflow.log_param("pipeline_name", pipeline_name)
        mlflow.log_param("run_id", run_id)

    # Expose to Prometheus via pushgateway
    metric_gauges = {}
    for name, value in model_metrics.items():
        if isinstance(value, (int, float)):
            gauge_name = f"pipeline_{name}".replace(" ", "_")
            gauge = Gauge(gauge_name, f"Pipeline metric: {name}")
            gauge.set(value)
            metric_gauges[gauge_name] = gauge

    try:
        push_to_gateway(
            "prometheus-pushgateway:9091",
            job=f"pipeline_{pipeline_name}",
            registry=None,
        )
        print("Metrics pushed to Prometheus pushgateway")
    except Exception as e:
        print(f"Warning: Could not push to Prometheus: {e}")

    return {"logged_metrics": len(model_metrics), "status": "success"}


@component
def custom_metric_calculator(
    predictions_path: str,
    ground_truth_path: str,
) -> dict:
    """Calculate custom business metrics beyond standard ML metrics."""
    import pandas as pd
    import numpy as np

    preds = pd.read_parquet(predictions_path)
    truth = pd.read_parquet(ground_truth_path)

    # Business-specific metrics
    errors = preds["prediction"] - truth["actual"]
    abs_errors = np.abs(errors)

    metrics = {
        "mean_absolute_error": float(np.mean(abs_errors)),
        "median_absolute_error": float(np.median(abs_errors)),
        "p90_absolute_error": float(np.percentile(abs_errors, 90)),
        "p95_absolute_error": float(np.percentile(abs_errors, 95)),
        "max_absolute_error": float(np.max(abs_errors)),
        "error_std": float(np.std(errors)),
        "bias": float(np.mean(errors)),
        "samples_evaluated": len(errors),
    }

    # Percent of predictions within tolerance
    tolerance = 0.1
    within_tolerance = np.mean(abs_errors / np.abs(truth["actual"]) < tolerance)
    metrics["within_tolerance_pct"] = float(within_tolerance * 100)

    return metrics
```

## Step 3: Implementing Error Handling and Retry Logic

Production pipelines must handle failures gracefully. Implement retry logic with exponential backoff and dead-letter handling.

```python
import time
import random
from typing import Callable


def with_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
) -> Callable:
    """Decorator for adding retry logic with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        jitter = random.uniform(0, delay * 0.1)
                        total_delay = delay + jitter
                        print(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {total_delay:.1f}s..."
                        )
                        time.sleep(total_delay)
                    else:
                        print(f"All {max_retries} retries exhausted")
            raise last_exception
        return wrapper
    return decorator


@component(
    base_image="python:3.11",
    packages_to_install=["requests"],
)
def resilient_api_call(
    endpoint: str,
    payload: dict,
    max_retries: int = 3,
) -> dict:
    """Make a resilient API call with retry logic."""
    import requests

    @with_retry(max_retries=max_retries)
    def call_api():
        response = requests.post(
            endpoint,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    try:
        result = call_api()
        print(f"API call succeeded: {endpoint}")
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"API call failed after retries: {e}")
        return {"status": "failed", "error": str(e)}


@component
def safe_data_loader(
    data_path: str,
    fallback_path: str = None,
) -> str:
    """Load data with fallback to a backup source on failure."""
    import os

    # Primary data source
    if os.path.exists(data_path):
        print(f"Loading from primary source: {data_path}")
        return data_path

    # Fallback to backup source
    if fallback_path and os.path.exists(fallback_path):
        print(f"Primary not found. Loading from fallback: {fallback_path}")
        return fallback_path

    # Graceful degradation
    print("No data source available. Generating synthetic fallback data.")
    fallback_data = "/tmp/synthetic_fallback.csv"
    with open(fallback_data, "w") as f:
        f.write("feature_1,feature_2,target\n")
        for i in range(100):
            f.write(f"{random.random()},{random.random()},{random.random()}\n")
    return fallback_data


@pipeline(name="resilient-pipeline")
def resilient_pipeline(
    primary_data_path: str = "/data/live/bike_sharing.csv",
    backup_data_path: str = "/data/backup/bike_sharing.csv",
):
    # Safe data loading with fallback
    data = safe_data_loader(
        data_path=primary_data_path,
        fallback_path=backup_data_path,
    )

    # Training with KFP-level retry
    train_task = logged_model_training(
        data_path=data,
        hyperparameters={"n_estimators": 200},
    )

    # Configure retry at the task level
    train_task.set_retry(
        num_retries=3,
        backoff_duration=10,           # seconds
        backoff_factor=2.0,
        backoff_max_duration=60,       # max 60 seconds between retries
    )

    # Model deployment with fallback
    deployment = resilient_api_call(
        endpoint="http://model-server:8000/deploy",
        payload={"model_path": train_task.output},
    )
```

## Step 4: Debugging Failed Pipeline Runs

KFP provides several tools for debugging. Learn to inspect failed runs, examine logs, and diagnose common failure modes.

```python
# Using the KFP SDK to debug failed runs
from kfp import Client

client = Client(host="http://localhost:8080")


def debug_failed_run(run_id: str):
    """Inspect a failed pipeline run and identify root causes."""
    # Get run details
    run_detail = client.get_run(run_id=run_id)
    print(f"Run: {run_detail.run.name}")
    print(f"Status: {run_detail.run.status}")
    print(f"Error: {run_detail.run.error}")

    # List all tasks in the run
    tasks = client.list_tasks(run_id=run_id)
    print(f"\nTasks ({len(tasks.tasks)}):")

    for task in tasks.tasks:
        status_symbol = "✓" if task.status == "Succeeded" else "✗"
        print(f"\n  {status_symbol} {task.name}")
        print(f"     Status: {task.status}")
        print(f"     Started: {task.started_at}")
        print(f"     Duration: {task.finished_at - task.started_at}")

        if task.error:
            print(f"     Error: {task.error.message}")
            print(f"     Exit code: {task.error.exit_code}")


# Common failure modes and diagnostics:

def check_common_failures(run_id: str):
    """Check for common pipeline failure patterns."""
    run_detail = client.get_run(run_id=run_id)
    error_msg = str(run_detail.run.error or "").lower()

    failures = {
        "OOM": any(term in error_msg for term in [
            "oom", "memory", "out of memory", "exit code 137",
        ]),
        "timeout": any(term in error_msg for term in [
            "timeout", "deadline", "timed out",
        ]),
        "missing_data": any(term in error_msg for term in [
            "file not found", "no such file", "does not exist",
        ]),
        "dependency_error": any(term in error_msg for term in [
            "module not found", "import error", "no module named",
        ]),
    }

    print("\nFailure analysis:")
    for failure_type, detected in failures.items():
        print(f"  {failure_type}: {'DETECTED' if detected else 'not detected'}")

    return failures


@component
def debug_component(
    data_path: str,
    enable_debug: bool = False,
) -> str:
    """Component with built-in debugging support."""
    import sys
    import traceback
    import pandas as pd

    if enable_debug:
        # Enable detailed tracing
        sys.settrace(lambda frame, event, arg: None)

    try:
        df = pd.read_csv(data_path)
        print(f"Data loaded: {len(df)} rows")
        return data_path

    except FileNotFoundError:
        print(f"ERROR: File not found: {data_path}")
        print(f"Current working directory contents:")
        import os
        for f in os.listdir("."):
            print(f"  {f}")
        raise

    except pd.errors.EmptyDataError:
        print(f"ERROR: File is empty: {data_path}")
        raise

    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        raise
```

Debugging workflow for pipeline failures:

```python
# Workflow: Debugging from the KFP UI or SDK

# 1. List recent failed runs
failed_runs = client.list_runs(
    experiment_name="production",
    page_size=20,
)

print("Recent failed runs:")
for run in (failed_runs.runs or []):
    if run.run.status == "Failed":
        print(f"  - {run.run.name}: {run.run.error}")

# 2. Download pod logs for a specific task
def get_task_logs(
    run_id: str,
    task_name: str,
) -> str:
    """Retrieve pod logs for a specific task in a run."""
    tasks = client.list_tasks(run_id=run_id)
    for task in tasks.tasks or []:
        if task.name == task_name:
            # Get logs via Kubernetes API
            print(f"Task pod: {task.pod_name}")
            print(f"Node: {task.node_name}")
            return task.detail

    return "Task not found"

# 3. Re-run with debugging enabled
def rerun_with_debug(
    original_run_id: str,
    debug_param: str = "enable_debug",
):
    """Re-run a failed pipeline with debug mode enabled."""
    run_detail = client.get_run(original_run_id)
    params = run_detail.pipeline_spec.parameters or {}

    # Enable debugging in parameters
    params[debug_param] = True

    # Create new run with debug enabled
    new_run = client.run_pipeline(
        experiment_id=run_detail.run.experiment_id,
        job_name=f"{run_detail.run.name}-debug",
        pipeline_id=run_detail.pipeline_spec.pipeline_id,
        params=params,
    )

    print(f"Debug run created: {new_run.run_id}")
    return new_run.run_id
```

## Step 5: Creating Monitoring Dashboards for Pipeline Health

Build comprehensive dashboards to track pipeline health, performance trends, and failure patterns.

```python
@component(
    base_image="python:3.11",
    packages_to_install=["jinja2"],
)
def generate_monitoring_report(
    run_history: list,
    output_format: str = "html",
) -> str:
    """Generate a monitoring report from pipeline run history."""
    import json
    from datetime import datetime

    # Calculate aggregate statistics
    total_runs = len(run_history)
    successful_runs = sum(
        1 for r in run_history if r.get("status") == "Succeeded"
    )
    failed_runs = total_runs - successful_runs
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

    avg_duration = 0
    durations = [r.get("duration_seconds", 0) for r in run_history if r.get("duration_seconds")]
    if durations:
        avg_duration = sum(durations) / len(durations)

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate_pct": round(success_rate, 2),
            "avg_duration_seconds": round(avg_duration, 2),
        },
        "recent_failures": [
            r for r in run_history
            if r.get("status") == "Failed"
        ][-10:],  # Last 10 failures
    }

    report_path = "/tmp/pipeline_monitoring_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nPipeline Health Report")
    print(f"{'='*40}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Avg Duration: {avg_duration:.1f}s")
    print(f"Total Runs: {total_runs}")
    print(f"Failures: {failed_runs}")

    return report_path
```

Dashboard configuration for Grafana:

```json
{
  "dashboard": {
    "title": "Kubeflow Pipeline Health",
    "panels": [
      {
        "title": "Pipeline Success Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "sum(pipeline_runs_total{status=\"Succeeded\"}) / sum(pipeline_runs_total) * 100",
            "legendFormat": "Success Rate"
          }
        ],
        "thresholds": [
          {"color": "red", "value": 90},
          {"color": "yellow", "value": 95},
          {"color": "green", "value": 100}
        ]
      },
      {
        "title": "Pipeline Failures Over Time",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(pipeline_runs_total{status=\"Failed\"}[1h]))",
            "legendFormat": "Failures/hour"
          }
        ]
      },
      {
        "title": "Model Performance Drift",
        "type": "timeseries",
        "targets": [
          {
            "expr": "pipeline_model_accuracy",
            "legendFormat": "{{model_name}}"
          }
        ]
      },
      {
        "title": "Pipeline Run Duration (P95)",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(pipeline_duration_seconds_bucket[1d])) by (le))",
            "legendFormat": "P95 Duration"
          }
        ]
      }
    ]
  }
}
```

Alerting rules for Prometheus:

```yaml
# prometheus-alerts.yaml
groups:
  - name: kubeflow-pipelines
    rules:
      - alert: PipelineHighFailureRate
        expr: |
          rate(pipeline_runs_total{status="Failed"}[1h])
          /
          rate(pipeline_runs_total[1h]) > 0.1
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Pipeline failure rate > 10% over last hour"

      - alert: ModelAccuracyDrop
        expr: |
          pipeline_model_accuracy < 0.80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Model accuracy dropped below 80%"

      - alert: PipelineRunTimeout
        expr: |
          pipeline_duration_seconds > 3600
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline run exceeding 1 hour expected duration"
```

## Summary

In this exercise, you:

1. Implemented structured JSON logging across pipeline components
2. Collected and exposed custom metrics to MLflow and Prometheus
3. Built resilient pipelines with retry logic and graceful degradation
4. Diagnosed failed runs using KFP debugging tools and SDK methods
5. Created monitoring dashboards and alerting rules for pipeline health

---

