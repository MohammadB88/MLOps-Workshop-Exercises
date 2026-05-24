# Exercise 2: Advanced Workflows

In this exercise, you will learn how to build sophisticated pipeline workflows using conditional execution, parallel loops, and fan-out/fan-in patterns in Kubeflow Pipelines.

## Learning Objectives

By the end of this exercise, you will be able to:
- Implement conditional branching with `kfp.dsl.Condition`
- Create parallel execution loops with `kfp.dsl.ParallelFor`
- Build fan-out/fan-in patterns for distributed processing
- Combine conditions with parallel execution for complex workflows
- Understand the DAG execution model and its implications

## Prerequisites

1. Completed Exercise 1: Basic Triggers
2. Kubeflow Pipelines SDK installed (`pip install kfp`)
3. Understanding of basic pipeline component definitions

!!! tip "MLOps Perspective"
    Production pipelines require sophisticated orchestration patterns. These skills enable scalable, reliable, and automated ML workflows.

## Step 1: Understanding Conditional Execution in KFP

Conditional execution allows pipelines to make data-driven decisions at runtime. KFP uses the `kfp.dsl.Condition` context manager to gate component execution based on upstream outputs.

```python
from kfp import dsl
from kfp.dsl import component

@component
def evaluate_data_quality(
    data_path: str,
    missing_threshold: float = 0.1,
) -> bool:
    """Evaluate whether dataset quality meets the threshold."""
    import pandas as pd

    df = pd.read_csv(data_path)
    missing_rate = df.isnull().sum().sum() / df.size

    print(f"Missing data rate: {missing_rate:.2%}")
    quality_ok = missing_rate <= missing_threshold

    return quality_ok

@component
def train_production_model(
    data_path: str,
    model_type: str = "random_forest",
) -> str:
    """Train a production-grade model on quality data."""
    import pickle
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(n_estimators=300, max_depth=15)
    model.fit([[0]], [0])  # Placeholder for actual training
    model_path = "/tmp/prod_model.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"Production model trained: {model_type}")
    return model_path


@component
def train_fallback_model(
    data_path: str,
) -> str:
    """Train a simpler fallback model when data quality is poor."""
    import pickle
    from sklearn.linear_model import LinearRegression

    model = LinearRegression()
    model.fit([[0]], [0])  # Placeholder
    model_path = "/tmp/fallback_model.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print("Fallback model trained")
    return model_path
```

## Step 2: Implementing if/else Branches with `kfp.dsl.Condition`

Use the `Condition` context manager to create branches. Only components inside the matching condition will execute. Note that KFP does not support else clauses natively; you model "else" as a second condition with the negated predicate.

```python
from kfp.dsl import Condition

@pipeline(name="conditional-training-pipeline")
def conditional_training_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    # Evaluate data quality first
    quality_task = evaluate_data_quality(
        data_path=data_path,
        missing_threshold=0.05,
    )

    # Branch 1: Data quality is good → train production model
    with Condition(
        quality_task.output == True,
        name="quality-ok",
    ):
        prod_model = train_production_model(
            data_path=data_path,
            model_type="random_forest",
        )

        # Nested condition inside the branch
        with Condition(
            prod_model.output != "",
            name="model-saved",
        ):
            print("Production model saved successfully")

    # Branch 2: Data quality is poor → train fallback model
    with Condition(
        quality_task.output == False,
        name="quality-fail",
    ):
        fallback_model = train_fallback_model(
            data_path=data_path,
        )
```

## Step 3: Creating Parallel Loops with `kfp.dsl.ParallelFor`

`ParallelFor` enables parallel execution of pipeline components over a list of items. This is essential for hyperparameter tuning, cross-validation, and multi-model training.

```python
from kfp.dsl import ParallelFor

@component
def train_model_with_params(
    data_path: str,
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
) -> dict:
    """Train a model with specific hyperparameters."""
    import time
    import random

    # Simulate training with given params
    time.sleep(random.uniform(1, 3))
    accuracy = random.uniform(0.80, 0.95)

    result = {
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "learning_rate": learning_rate,
        "accuracy": accuracy,
    }
    print(f"Trained: n_estimators={n_estimators}, "
          f"max_depth={max_depth}, accuracy={accuracy:.3f}")
    return result


@component
def select_best_model(
    results: list,
) -> dict:
    """Select the best model from a list of results."""
    best = max(results, key=lambda r: r["accuracy"])
    print(
        f"Best model: n_estimators={best['n_estimators']}, "
        f"max_depth={best['max_depth']}, "
        f"accuracy={best['accuracy']:.3f}"
    )
    return best


@pipeline(name="parallel-hyperparameter-tuning")
def hyperparameter_tuning_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    # Define hyperparameter grid
    param_grid = [
        {"n_estimators": 50, "max_depth": 5, "learning_rate": 0.01},
        {"n_estimators": 100, "max_depth": 10, "learning_rate": 0.01},
        {"n_estimators": 200, "max_depth": 10, "learning_rate": 0.05},
        {"n_estimators": 100, "max_depth": 15, "learning_rate": 0.05},
        {"n_estimators": 300, "max_depth": 20, "learning_rate": 0.1},
    ]

    results = []

    # Parallel loop over hyperparameter combinations
    with ParallelFor(param_grid, name="hyperparameter-search") as params:
        training_result = train_model_with_params(
            data_path=data_path,
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
        )
        results.append(training_result)

    # Fan-in: select best model after all parallel runs complete
    best_model = select_best_model(results=results)
```

## Step 4: Building Fan-Out/Fan-In Patterns

Fan-out/fan-in is a powerful parallel processing pattern: split work across multiple parallel tasks (fan-out) then aggregate results (fan-in).

```python
@component
def split_data_by_region(
    data_path: str,
    regions: list,
) -> list:
    """Split dataset into region-specific subsets."""
    import pandas as pd

    df = pd.read_csv(data_path)
    split_paths = []

    for region in regions:
        region_df = df[df["region"] == region]
        path = f"/tmp/region_{region}.csv"
        region_df.to_csv(path, index=False)
        split_paths.append(path)
        print(f"Created split for {region}: {len(region_df)} rows")

    return split_paths


@component
def train_region_model(
    region_data: str,
    region_name: str,
) -> dict:
    """Train a region-specific model."""
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor

    df = pd.read_csv(region_data)
    model = RandomForestRegressor(n_estimators=100)
    model.fit(df.drop("target", axis=1), df["target"])
    score = model.score(df.drop("target", axis=1), df["target"])

    return {
        "region": region_name,
        "score": score,
        "samples": len(df),
    }


@component
def ensemble_region_models(
    region_results: list,
) -> str:
    """Combine region models into a global ensemble."""
    import json

    total_score = sum(r["score"] * r["samples"] for r in region_results)
    total_samples = sum(r["samples"] for r in region_results)
    weighted_avg_score = total_score / total_samples

    print(f"Ensemble weighted average score: {weighted_avg_score:.4f}")

    report_path = "/tmp/ensemble_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "regions": region_results,
            "ensemble_score": weighted_avg_score,
        }, f)

    return report_path


@pipeline(name="fan-out-fan-in-pipeline")
def fan_out_fan_in_pipeline(
    data_path: str = "/data/bike_sharing.csv",
):
    regions = ["north", "south", "east", "west"]

    # Fan-out: split data into region-specific chunks
    split_paths = split_data_by_region(
        data_path=data_path,
        regions=regions,
    )

    # Fan-in: train one model per region in parallel
    region_results = []
    with ParallelFor(
        [{"path": p, "name": n} for p, n in zip(
            split_paths.output, regions
        )],
        name="region-training",
    ) as item:
        result = train_region_model(
            region_data=item["path"],
            region_name=item["name"],
        )
        region_results.append(result)

    # Aggregate: combine all region models
    ensemble_report = ensemble_region_models(
        region_results=region_results,
    )
```

## Step 5: Combining Conditions with Parallel Execution

Complex workflows often need both conditional branching and parallel loops together. This example combines both patterns for a comprehensive training strategy.

```python
@pipeline(name="advanced-ml-workflow")
def advanced_ml_workflow(
    data_path: str = "/data/bike_sharing.csv",
    enable_hyperparameter_tuning: bool = True,
):
    # Always validate data first
    quality_check = evaluate_data_quality(
        data_path=data_path,
        missing_threshold=0.1,
    )

    # Condition 1: Data quality is acceptable
    with Condition(
        quality_check.output == True,
        name="quality-acceptable",
    ):
        # Parallel hyperparameter tuning (only if enabled)
        with Condition(
            enable_hyperparameter_tuning == True,
            name="tuning-enabled",
        ):
            param_grid = [
                {"n_estimators": 100, "max_depth": 10},
                {"n_estimators": 200, "max_depth": 15},
                {"n_estimators": 300, "max_depth": 20},
            ]

            results = []
            with ParallelFor(param_grid, name="tuning-loop") as params:
                result = train_model_with_params(
                    data_path=data_path,
                    n_estimators=params["n_estimators"],
                    max_depth=params["max_depth"],
                    learning_rate=0.1,
                )
                results.append(result)

            # Fan-in to select best model
            select_best_model(results=results)

        # Default training without tuning
        with Condition(
            enable_hyperparameter_tuning == False,
            name="tuning-disabled",
        ):
            train_production_model(data_path=data_path)

    # Condition 2: Data quality is poor
    with Condition(
        quality_check.output == False,
        name="quality-unacceptable",
    ):
        train_fallback_model(data_path=data_path)
```

## Summary

In this exercise, you:
1. Defined conditional branches using `kfp.dsl.Condition` to gate component execution
2. Implemented if/else patterns for data-quality-driven model selection
3. Created parallel hyperparameter sweeps with `kfp.dsl.ParallelFor`
4. Built fan-out/fan-in patterns for region-specific model training
5. Combined conditions with parallel execution for sophisticated multi-branch workflows

---

<div style="display: flex; justify-content: space-between;">
<a href="../01_basic_triggers/" class="md-button">← Previous</a>
<a href="../03_scheduling_automation/" class="md-button">Next →</a>
</div>
