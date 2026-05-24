# Exercise 4: Optimization & Scaling

In this exercise, you will learn how to optimize and scale Kubeflow Pipelines for production workloads by configuring resources, caching, and parallel execution strategies.

## Learning Objectives

By the end of this exercise, you will be able to:
- Configure CPU, memory, and GPU resource requests and limits for components
- Enable and manage pipeline caching to accelerate iterative development
- Implement parallel execution with resource-aware scheduling
- Optimize artifact storage and implement cleanup policies
- Understand KFP's execution model for cost-effective scaling

## Prerequisites

1. Completed Exercise 3: Scheduling & Automation
2. Access to a KFP environment with GPU nodes (for GPU section)
3. Understanding of Kubernetes resource management concepts

## Step 1: Understanding Resource Requests and Limits in KFP

KFP components run as Kubernetes pods. Setting appropriate resource requests and limits ensures reliable execution and efficient cluster utilization.

```python
from kfp import dsl
from kfp.dsl import component, pipeline

@component(
    base_image="python:3.11",
    packages_to_install=["pandas", "scikit-learn"],
)
def cpu_bound_component(
    data_path: str,
) -> str:
    """A CPU-intensive data processing component."""
    import pandas as pd
    import time

    df = pd.read_csv(data_path)
    # CPU-intensive operations
    for col in df.select_dtypes(include="number").columns:
        df[f"{col}_rolling"] = df[col].rolling(window=7).mean()

    processed_path = "/tmp/processed_data.csv"
    df.to_csv(processed_path, index=False)
    return processed_path


@component(
    base_image="python:3.11",
    packages_to_install=["pandas", "torch"],
)
def gpu_bound_component(
    model_path: str,
) -> str:
    """A GPU-intensive model training component."""
    import torch
    import time

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("No GPU available, using CPU")

    # Simulate training
    time.sleep(10)
    return "/tmp/trained_model.pt"
```

Apply resource constraints to components. Resources are set using the `set_cpu_limit`, `set_memory_limit`, and `set_gpu_limit` methods on the task object:

```python
@pipeline(name="resource-optimized-pipeline")
def resource_optimized_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    # CPU-intensive data processing
    process_task = cpu_bound_component(data_path=data_path)
    process_task.set_cpu_request("2")
    process_task.set_cpu_limit("4")
    process_task.set_memory_request("4Gi")
    process_task.set_memory_limit("8Gi")

    # GPU training
    train_task = gpu_bound_component(model_path=process_task.output)
    train_task.set_cpu_request("4")
    train_task.set_cpu_limit("8")
    train_task.set_memory_request("16Gi")
    train_task.set_memory_limit("32Gi")
    train_task.set_gpu_limit(1)

    print(f"Data processing resources: CPU 2-4 cores, 4-8Gi RAM")
    print(f"Training resources: CPU 4-8 cores, 16-32Gi RAM, 1 GPU")
```

## Step 2: Configuring CPU, Memory, and GPU for Pipeline Components

Resource tuning depends on workload characteristics. Use these patterns for common ML task types.

```python
from kfp.dsl import component

# Lightweight data validation component
@component
def validate_data(
    data_path: str,
) -> dict:
    """Validate data quality — lightweight task."""
    import pandas as pd

    df = pd.read_csv(data_path)
    report = {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_cells": int(df.isnull().sum().sum()),
    }
    return report


# Memory-intensive feature engineering
@component
def engineer_features(
    data_path: str,
) -> str:
    """Feature engineering — memory-intensive due to one-hot encoding."""
    import pandas as pd

    df = pd.read_csv(data_path)
    df_encoded = pd.get_dummies(df, columns=df.select_dtypes(
        include="object"
    ).columns)
    output_path = "/tmp/features.parquet"
    df_encoded.to_parquet(output_path)
    return output_path


# GPU-accelerated deep learning training
@component(base_image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime")
def deep_learning_train(
    features_path: str,
    epochs: int = 50,
) -> str:
    """Deep learning training requiring GPU acceleration."""
    import torch
    import torch.nn as nn

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    model = nn.Sequential(
        nn.Linear(128, 256),
        nn.ReLU(),
        nn.Dropout(0.2),
        nn.Linear(256, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
    ).to(device)

    model_path = "/tmp/dl_model.pt"
    torch.save(model.state_dict(), model_path)
    return model_path


@pipeline(name="resource-optimized-pipeline")
def resource_optimized_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    # Task 1: Validation — small footprint
    validate_task = validate_data(data_path=data_path)
    validate_task.set_cpu_request("500m")      # 0.5 CPU
    validate_task.set_cpu_limit("1")
    validate_task.set_memory_request("512Mi")   # 512 MB
    validate_task.set_memory_limit("1Gi")

    # Task 2: Feature engineering — memory-heavy
    feature_task = engineer_features(
        data_path=validate_task.outputs["report"]
    )
    feature_task.set_cpu_request("2")
    feature_task.set_cpu_limit("4")
    feature_task.set_memory_request("8Gi")      # 8 GB for encoding
    feature_task.set_memory_limit("16Gi")
    feature_task.add_node_selector_constraint(
        "node.kubernetes.io/instance-type",
        "memory-optimized",
    )

    # Task 3: Deep learning — GPU required
    train_task = deep_learning_train(
        features_path=feature_task.output,
        epochs=100,
    )
    train_task.set_cpu_request("4")
    train_task.set_cpu_limit("8")
    train_task.set_memory_request("16Gi")
    train_task.set_memory_limit("32Gi")
    train_task.set_gpu_limit(1)
    train_task.add_node_selector_constraint(
        "nvidia.com/gpu.present",
        "true",
    )
```

Resource allocation guidelines for ML workloads:

| Workload Type          | CPU Request | CPU Limit | Memory   | GPU | Example                       |
|------------------------|-------------|-----------|----------|-----|-------------------------------|
| Data validation        | 500m        | 1         | 512Mi    | 0   | Schema checks, null counts    |
| Feature engineering    | 2           | 4         | 8-16Gi   | 0   | One-hot encoding, scaling     |
| Classical ML training  | 4           | 8         | 8-16Gi   | 0   | Random Forest, XGBoost        |
| Deep learning training | 4-8         | 8-16      | 16-64Gi  | 1-4 | Transformer, CNN training     |
| Model serving          | 1-2         | 2-4       | 2-8Gi    | 0-1 | FastAPI inference endpoint    |

## Step 3: Enabling and Managing Pipeline Caching

KFP caches component outputs to avoid redundant re-execution. Caching uses the component's name, image, code, and inputs as the cache key.

```python
# Caching is enabled by default in KFP.
# The cache key is a hash of:
#   1. Component implementation (code/image)
#   2. All input parameter values
#   3. Upstream artifact fingerprints
#
# A cache hit reuses previous outputs without re-execution.

# To disable caching for a specific task:
@dsl.pipeline(name="caching-demo")
def caching_demo_pipeline(
    data_path: str,
    run_id: str,
):
    # Task 1: Always re-execute (cache disabled)
    validate_task = validate_data(data_path=data_path)
    validate_task.execution_options.caching_strategy.max_cache_staleness = "0s"

    # Task 2: Cache for 24 hours
    feature_task = engineer_features(data_path=data_path)
    feature_task.execution_options.caching_strategy.max_cache_staleness = "24h"

    # Task 3: Use caching (default — indefinite)
    train_task = cpu_bound_component(data_path=data_path)
    # Cache is valid indefinitely by default


# Cache-aware component design:
# Use deterministic inputs to maximize cache hits
@component
def deterministic_feature_engineering(
    data_hash: str,         # ← Deterministic input for cache key
    n_features: int,
) -> str:
    """Feature engineering that benefits from caching."""
    import hashlib

    # Because 'data_hash' is an explicit input, changing data
    # invalidates the cache automatically
    cache_key = hashlib.md5(
        f"{data_hash}-{n_features}".encode()
    ).hexdigest()
    print(f"Cache key: {cache_key}")

    features_path = f"/tmp/features_{cache_key}.parquet"
    return features_path
```

Cache management strategies:

```python
# Strategy 1: Development mode — disable caching
@dsl.pipeline(name="dev-pipeline")
def dev_pipeline(data_path: str):
    task = validate_data(data_path=data_path)
    task.execution_options.caching_strategy.max_cache_staleness = "0s"
    # Every run re-executes — useful during development

# Strategy 2: Production mode — use caching with staleness
@dsl.pipeline(name="prod-pipeline")
def prod_pipeline(data_path: str):
    task = engineer_features(data_path=data_path)
    task.execution_options.caching_strategy.max_cache_staleness = "168h"
    # Reuses cached results for up to 1 week

# Strategy 3: Selective caching — cache stable steps only
@dsl.pipeline(name="selective-cache-pipeline")
def selective_cache_pipeline(data_path: str):
    # Step 1: Cache this — data prep logic is stable
    prep = validate_data(data_path=data_path)
    prep.execution_options.caching_strategy.max_cache_staleness = "72h"

    # Step 2: Don't cache this — training varies
    train = cpu_bound_component(data_path=data_path)
    train.execution_options.caching_strategy.max_cache_staleness = "0s"
```

## Step 4: Implementing Parallel Execution with Resource Constraints

Effective parallel execution requires balancing concurrency against available cluster resources. Use these patterns to control parallelism.

```python
@component
def heavy_computation(
    chunk_id: int,
    data_path: str,
) -> dict:
    """A resource-intensive computation task."""
    import time
    import random

    compute_time = random.uniform(30, 120)
    time.sleep(compute_time)

    return {
        "chunk_id": chunk_id,
        "compute_time": compute_time,
        "result": f"processed_chunk_{chunk_id}",
    }


@component
def aggregate_results(
    chunk_results: list,
) -> dict:
    """Aggregate results from parallel computation tasks."""
    total_time = sum(r["compute_time"] for r in chunk_results)
    print(f"Aggregated {len(chunk_results)} chunks")
    print(f"Total compute time: {total_time:.1f}s")
    return {"total_time": total_time, "chunks": len(chunk_results)}


@pipeline(name="parallel-with-resource-constraints")
def parallel_resource_pipeline(
    data_path: str = "/data/large_dataset.csv",
    num_chunks: int = 10,
):
    # Process chunks in parallel with constrained resources
    chunk_ids = list(range(num_chunks))

    chunk_results = []

    with dsl.ParallelFor(chunk_ids, name="parallel-chunks") as chunk_id:
        task = heavy_computation(
            chunk_id=chunk_id,
            data_path=data_path,
        )

        # Each parallel task gets limited resources
        task.set_cpu_request("1")
        task.set_cpu_limit("2")
        task.set_memory_request("1Gi")
        task.set_memory_limit("2Gi")

        # Limit pod parallelism at the cluster level
        # Set via KFP's pod metadata:
        task.set_display_name(f"chunk-{chunk_id}")

        chunk_results.append(task.output)

    # Aggregate after all parallel tasks complete
    aggregate = aggregate_results(chunk_results=chunk_results)
    aggregate.set_cpu_request("500m")
    aggregate.set_memory_request("512Mi")
```

For controlling concurrency across the entire pipeline:

```python
# Set pod defaults for all tasks in a pipeline
@dsl.pipeline(
    name="controlled-parallelism",
    description="Pipeline with controlled parallelism",
)
def controlled_parallelism_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    # Configure pod defaults at the pipeline level
    # (applied to all tasks unless overridden)

    # Parallel processing with max 3 concurrent pods
    chunks = list(range(5))

    with dsl.ParallelFor(
        chunks,
        name="batch-processing",
        parallelism_limit=3,     # Max 3 concurrent pods
    ) as chunk:
        task = heavy_computation(
            chunk_id=chunk,
            data_path=data_path,
        )
        task.set_cpu_request("2")
        task.set_memory_request("4Gi")
```

## Step 5: Optimizing Artifact Storage and Cleanup

Pipeline artifacts (metrics, models, intermediate data) accumulate quickly. Implement proper storage management to control costs and maintain performance.

```python
@component
def generate_intermediate_data(
    dataset_size_mb: int = 100,
) -> str:
    """Generate large intermediate artifacts."""
    import pandas as pd
    import numpy as np

    n_rows = (dataset_size_mb * 1024 * 1024) // 100  # ~100 bytes per row
    df = pd.DataFrame(
        np.random.randn(n_rows, 10),
        columns=[f"feature_{i}" for i in range(10)],
    )

    path = "/tmp/intermediate_data.parquet"
    df.to_parquet(path, compression="snappy")
    file_size_mb = len(df) * 100 / (1024 * 1024)
    print(f"Generated {file_size_mb:.1f} MB of intermediate data")
    return path


@component
def cleanup_artifacts(
    retention_days: int = 7,
    artifact_prefix: str = "pipeline-artifacts",
) -> int:
    """Clean up old pipeline artifacts from storage."""
    import os
    import time
    from datetime import datetime, timedelta

    artifact_dir = "/artifacts"
    cutoff = datetime.now() - timedelta(days=retention_days)
    cutoff_ts = cutoff.timestamp()

    deleted_count = 0
    deleted_size_mb = 0

    for root, dirs, files in os.walk(artifact_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if file.startswith(artifact_prefix):
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < cutoff_ts:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                    deleted_size_mb += file_size / (1024 * 1024)

    print(f"Cleaned {deleted_count} artifacts ({deleted_size_mb:.1f} MB)")
    return deleted_count


@component
def compress_and_archive(
    source_pattern: str,
    archive_name: str,
) -> str:
    """Compress and archive pipeline outputs for long-term storage."""
    import tarfile
    import os
    import glob

    archive_path = f"/tmp/{archive_name}.tar.gz"
    files = glob.glob(source_pattern)

    with tarfile.open(archive_path, "w:gz") as tar:
        for f in files:
            tar.add(f, arcname=os.path.basename(f))

    archive_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"Archived {len(files)} files to {archive_path}")
    print(f"Archive size: {archive_size_mb:.1f} MB")
    return archive_path


@pipeline(name="artifact-management-pipeline")
def artifact_management_pipeline(
    data_path: str = "/data/bike_sharing.csv",
    enable_cleanup: bool = True,
):
    # Generate intermediate data
    intermediate = generate_intermediate_data(dataset_size_mb=200)
    intermediate.set_cpu_request("1")
    intermediate.set_memory_request("2Gi")

    # Run main training
    train_result = cpu_bound_component(data_path=intermediate.output)
    train_result.set_cpu_request("2")
    train_result.set_memory_request("4Gi")

    # Optional: compress final model for archival
    archive = compress_and_archive(
        source_pattern="/tmp/model_*",
        archive_name=f"model-archive",
    )

    # Optional: run cleanup
    with dsl.Condition(
        enable_cleanup == True,
        name="cleanup-old-artifacts",
    ):
        cleanup_artifacts(
            retention_days=30,
            artifact_prefix="pipeline-artifacts",
        )
```

Best practices for artifact management:

```python
# 1. Use named outputs for explicit artifact tracking
@component
def train_with_artifacts(
    data_path: str,
) -> str:
    """Training with explicitly named outputs."""
    import pickle
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(n_estimators=100)
    artifact_path = "/artifacts/model.pkl"
    with open(artifact_path, "wb") as f:
        pickle.dump(model, f)
    return artifact_path


# 2. Set output artifact path conventions
# /artifacts/{pipeline_name}/{run_id}/{component_name}/{output_name}

# 3. Configure artifact retention via KFP API
# client.create_recurring_run(
#     ...
#     pipeline_spec={
#         "artifact_retention_policy": {
#             "max_artifact_size_gb": 50,
#             "max_artifact_count": 100,
#             "retention_days": 90,
#         }
#     }
# )
```

## Summary

In this exercise, you:
1. Configured CPU, memory, and GPU resource requests and limits for pipeline components
2. Applied caching strategies to optimize iterative development cycles
3. Implemented parallel execution with concurrency limits and resource constraints
4. Designed artifact management with compression, archival, and cleanup policies
5. Learned resource allocation patterns for different ML workload types

---

<div style="display: flex; justify-content: space-between;">
<a href="../03_scheduling_automation/" class="md-button">← Previous</a>
<a href="../05_monitoring_debugging/" class="md-button">Next →</a>
</div>
