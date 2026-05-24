# Exercise 2: Governance Implementation

## Objective

In this exercise, you will:
1. Connect to an MLflow tracking server and manage experiments
2. Create experiments with governance metadata tags
3. Search and filter experiments by compliance tags
4. Transition model versions through staging and production stages
5. Implement approval workflows using the MLflow Model Registry

## Prerequisites

- MLflow 2.x installed (`pip install mlflow`)
- Access to an MLflow tracking server or local `mlruns` directory
- A trained model logged to MLflow from a previous exercise
- Basic familiarity with the MLflow Model Registry

## Step 1: Setting Up the MLflow Client

Initialize the MLflow client and configure the tracking URI:

```python
import mlflow
from mlflow import MlflowClient
from datetime import datetime

# Configure tracking URI (local or remote)
mlflow.set_tracking_uri("http://mlflow-tracking.mlflow.svc.cluster.local:80")
client = MlflowClient()

# Verify connection
experiments = client.search_experiments()
print(f"Connected. Found {len(experiments)} experiments.")
```

## Step 2: Creating Experiments with Governance Tags

Tag experiments with governance metadata for compliance tracking:

```python
import time

GOVERNANCE_TAGS = {
    "owner": "mlops-team",
    "compliance_level": "high",
    "review_status": "pending",
    "data_classification": "confidential",
    "business_unit": "forecasting",
    "retention_period_days": "365",
}


def create_governed_experiment(name: str, tags: dict | None = None) -> str:
    """Create an experiment with governance tags."""
    exp_id = mlflow.create_experiment(
        name,
        tags=tags or GOVERNANCE_TAGS,
    )
    print(f"Created experiment '{name}' (ID: {exp_id})")
    for k, v in (tags or GOVERNANCE_TAGS).items():
        print(f"  Tag: {k} = {v}")
    return exp_id


# Create experiments for different compliance levels
exp_low = create_governed_experiment(
    "bike-demand-v1",
    {"owner": "mlops-team", "compliance_level": "low",
     "review_status": "approved", "data_classification": "public"},
)

exp_high = create_governed_experiment(
    "customer-churn-v1",
    {"owner": "compliance-team", "compliance_level": "high",
     "review_status": "pending", "data_classification": "pii"},
)
```

## Step 3: Searching Experiments by Tag

Query experiments using governance tags as filters:

```python
def search_experiments_by_tag(key: str, value: str) -> list:
    """Search experiments with a specific tag key-value pair."""
    results = client.search_experiments(
        filter_string=f"tags.{key} = '{value}'"
    )
    return results


# Find all high-compliance experiments
high_compliance = search_experiments_by_tag("compliance_level", "high")
print("High-compliance experiments:")
for exp in high_compliance:
    print(f"  - {exp.name} (ID: {exp.experiment_id})")

# Find all experiments pending review
pending = search_experiments_by_tag("review_status", "pending")
print(f"\nPending review ({len(pending)}):")
for exp in pending:
    tags = {k: v for k, v in exp.tags.items()
            if k in GOVERNANCE_TAGS}
    print(f"  - {exp.name}: {tags}")
```

## Step 4: Transitioning Models Through Stages

Register a model and promote it through governance stages:

```python
RUN_NAME = f"governance-demo-{int(time.time())}"

with mlflow.start_run(run_name=RUN_NAME) as run:
    mlflow.log_param("model_type", "random_forest")
    mlflow.log_metric("rmse", 42.5)
    mlflow.sklearn.log_model(
        sk_model="dummy_model",  # Replace with actual model
        artifact_path="model",
        registered_model_name="bike_demand_predictor",
    )
    run_id = run.info.run_id

model_name = "bike_demand_predictor"
latest_version = client.get_latest_versions(model_name, stages=["None"])[0]
version = latest_version.version
print(f"Registered model v{version} with run ID {run_id}")


# Transition through governance stages
def transition_with_approval(model_name: str, version: str,
                              stage: str, approver: str):
    """Transition a model version to a new stage."""
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
    )
    # Add governance metadata about the transition
    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="approved_by",
        value=approver,
    )
    client.set_model_version_tag(
        name=model_name,
        version=version,
        key="transition_timestamp",
        value=datetime.utcnow().isoformat(),
    )
    print(f"Model {model_name} v{version} -> {stage} "
          f"(approved by {approver})")


# Promote step by step
transition_with_approval(model_name, version, "Staging", "data-scientist")
transition_with_approval(model_name, version, "Production", "mlops-lead")
```

## Step 5: Implementing Approval Workflows

Build a simple approval workflow that enforces governance gates:

```python
class GovernanceGate:
    """Enforces governance rules before model promotion."""

    REQUIRED_TAGS = [
        "review_status",
        "compliance_level",
        "owner",
    ]

    @classmethod
    def check_experiment_approval(cls, experiment_id: str) -> bool:
        """Verify experiment tags meet governance requirements."""
        exp = client.get_experiment(experiment_id)
        missing = [
            tag for tag in cls.REQUIRED_TAGS
            if tag not in exp.tags
        ]
        if missing:
            print(f"Gate BLOCKED: missing tags {missing}")
            return False
        if exp.tags.get("review_status") != "approved":
            print(f"Gate BLOCKED: review_status = "
                  f"'{exp.tags.get('review_status')}'")
            return False
        print(f"Gate PASSED for experiment '{exp.name}'")
        return True

    @classmethod
    def promote_to_production(cls, model_name: str, version: str):
        """Only promote if all gates pass."""
        model_version = client.get_model_version(model_name, version)
        exp_id = model_version.run_id  # Simplified; in practice
                                          # resolve experiment ID
        if cls.check_experiment_approval(exp_id):
            transition_with_approval(
                model_name, version, "Production", "auto-gate"
            )
        else:
            print("Promotion rejected: governance checks failed")


# Run the approval gate
GovernanceGate.promote_to_production(
    model_name, str(int(version) + 1)
)
```

## Summary

In this exercise, you:
1. Connected to MLflow and explored available experiments
2. Created experiments with governance tags for compliance tracking
3. Searched and filtered experiments by tag values
4. Transitioned model versions through Staging and Production stages
5. Built an approval workflow using governance gates

---

<div style="display: flex; justify-content: flex-end;">
<a href="../03_audit_logging/" class="md-button">Next →</a>
</div>
