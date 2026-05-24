# Exercise 4: Compliance Reporting

## Objective

In this exercise, you will:
1. Understand GDPR requirements as they apply to ML systems
2. Generate a Model Card from MLflow experiment metadata
3. Create a compliance report summary with data lineage
4. Simulate a Data Subject Access Request (DSAR) workflow
5. Export compliance documentation for auditors

## Prerequisites

- MLflow 2.x installed (`pip install mlflow`)
- A completed experiment with logged model in MLflow
- `pandas` and `json` libraries available
- Understanding of GDPR principles (right to access, right to erasure)

!!! tip "MLOps Perspective"
    Security and compliance are foundational to production ML systems. These practices protect models, data, and users while meeting regulatory requirements.

## Step 1: Understanding GDPR Requirements for ML

Key GDPR articles that impact ML pipelines:

| Article | Requirement | ML Implication |
|---------|-------------|----------------|
| Art. 5 | Lawfulness, fairness, transparency | Document model purpose and data sources |
| Art. 13 | Right to be informed | Provide clear model documentation |
| Art. 15 | Right of access | Enable data subject access requests |
| Art. 17 | Right to erasure | Support model unlearning or retraction |
| Art. 22 | Automated decision-making | Log and explain model predictions |
| Art. 35 | Data Protection Impact Assessment | Maintain model risk documentation |

Set up the compliance reporting environment:

```python
import json
import mlflow
from mlflow import MlflowClient
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from typing import Any
```

## Step 2: Generating a Model Card from MLflow

Extract MLflow run metadata to build a standard Model Card:

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelCard:
    model_name: str
    model_version: str
    owner: str
    creation_date: str
    model_type: str
    dataset_description: str
    intended_use: str
    limitations: str
    performance_metrics: dict
    compliance_level: str
    training_data_sources: list[str] = field(default_factory=list)
    ethical_considerations: str = ""


def generate_model_card_from_mlflow(
    experiment_name: str,
    run_id: str,
) -> ModelCard:
    """Build a Model Card from MLflow run metadata."""
    client = MlflowClient()
    run = client.get_run(run_id)
    exp = client.get_experiment(run.info.experiment_id)
    tags = run.data.tags
    params = run.data.params
    metrics = run.data.metrics

    card = ModelCard(
        model_name=experiment_name,
        model_version=tags.get("mlflow.log-model.history", "v1"),
        owner=exp.tags.get("owner", "unknown"),
        creation_date=datetime.fromtimestamp(
            run.info.start_time / 1000
        ).isoformat(),
        model_type=params.get("model_type", "random_forest"),
        dataset_description=(
            "Bike sharing dataset from UCI ML Repository. "
            "Contains hourly rental data with weather and "
            "seasonal features."
        ),
        intended_use=(
            "Forecasting hourly bike rental demand for "
            "city planning and resource allocation."
        ),
        limitations=(
            "Model trained on historical data only; "
            "does not account for突发事件 or policy changes."
        ),
        performance_metrics=dict(metrics),
        compliance_level=exp.tags.get(
            "compliance_level", "low"
        ),
        training_data_sources=[
            "UCI Bike Sharing Dataset (2011-2012)",
        ],
        ethical_considerations=(
            "No personally identifiable information (PII) "
            "is used in training features."
        ),
    )
    return card


# Example: generate a model card (use a real run ID)
# card = generate_model_card_from_mlflow(
#     "bike-demand-v1", "a1b2c3d4e5f6..."
# )
# print(json.dumps(asdict(card), indent=2))
```

## Step 3: Creating Compliance Report Summaries

Aggregate metadata from multiple MLflow runs into a compliance report:

```python
class ComplianceReport:
    """Aggregate compliance documentation for a model."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.client = MlflowClient()
        self.sections = {}

    def add_section(self, name: str, content: Any):
        self.sections[name] = content

    def generate(self) -> dict:
        """Assemble the final compliance report."""
        return {
            "report_title": f"Compliance Report: {self.model_name}",
            "generated_at": datetime.utcnow().isoformat(),
            "model_name": self.model_name,
            "sections": self.sections,
            "certification": {
                "compliant": all(
                    self._check_section(s)
                    for s in self.sections.values()
                ),
                "reviewed_by": None,
                "review_date": None,
            },
        }

    def _check_section(self, section: Any) -> bool:
        """Simple validation that a section is populated."""
        if isinstance(section, dict):
            return len(section) > 0
        if isinstance(section, list):
            return len(section) > 0
        return bool(section)

    def export(self, path: str):
        """Write report to JSON file."""
        report = self.generate()
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Compliance report saved: {path}")


# Build a compliance report
report = ComplianceReport("bike_demand_predictor")
report.add_section("data_governance", {
    "data_sources": ["UCI Bike Sharing Dataset"],
    "retention_policy_days": 365,
    "anonymization": "No PII in features",
})
report.add_section("model_governance", {
    "training_owner": "mlops-team",
    "review_status": "approved",
    "stage": "production",
    "approval_date": "2026-01-15",
})
report.add_section("risk_assessment", {
    "fairness_checked": True,
    "bias_metrics": {"demographic_parity": 0.02},
    "explainability": "SHAP values available",
})

report.export("compliance_report.json")
```

## Step 4: Simulating a Data Subject Access Request (DSAR)

GDPR Article 15 gives individuals the right to access their data. Simulate this:

```python
import hashlib


class DSARHandler:
    """Handles Data Subject Access Requests for ML systems."""

    def __init__(self, audit_log_path: str = "ml_audit_log.jsonl"):
        self.audit_log_path = audit_log_path

    def _anonymize_event(self, event: dict) -> dict:
        """Remove direct identifiers from an event record."""
        safe = dict(event)
        # Hash the user_id for pseudonymization
        if "user_id" in safe:
            safe["user_id"] = hashlib.sha256(
                safe["user_id"].encode()
            ).hexdigest()[:16]
        return safe

    def find_events_for_user(
        self, user_id: str, anonymize: bool = True
    ) -> list[dict]:
        """Retrieve all prediction events involving a user."""
        import pandas as pd

        if not Path(self.audit_log_path).exists():
            return []

        df = pd.read_json(self.audit_log_path, lines=True)
        user_events = df[df["user_id"] == user_id].to_dict(
            orient="records"
        )

        if anonymize:
            user_events = [
                self._anonymize_event(e) for e in user_events
            ]

        return user_events

    def generate_dsar_report(
        self, user_id: str, output_path: str
    ) -> dict:
        """Generate a complete DSAR response."""
        events = self.find_events_for_user(user_id, anonymize=True)
        dsar = {
            "request_type": "Data Subject Access Request",
            "request_date": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "articles": ["GDPR Art. 15"],
            "data_found": len(events) > 0,
            "event_count": len(events),
            "events": events,
            "disclaimer": (
                "Personal data has been pseudonymized. "
                "For full erasure requests, see Art. 17."
            ),
        }
        with open(output_path, "w") as f:
            json.dump(dsar, f, indent=2, default=str)
        print(f"DSAR report saved: {output_path}")
        return dsar

    def delete_user_data(self, user_id: str) -> int:
        """Simulate right to erasure (Art. 17) by removing entries."""
        import pandas as pd

        if not Path(self.audit_log_path).exists():
            return 0

        df = pd.read_json(self.audit_log_path, lines=True)
        before = len(df)
        df = df[df["user_id"] != user_id]
        removed = before - len(df)

        # Rewrite the log without the user's entries
        df.to_json(
            self.audit_log_path, orient="records", lines=True
        )
        print(f"Right to erasure: removed {removed} records for {user_id}")
        return removed


# Simulate a DSAR
dsar = DSARHandler("ml_audit_log.jsonl")
dsar.generate_dsar_report("user-1", "dsar_user-1.json")
```

## Step 5: Exporting Compliance Documentation

Generate a complete compliance package suitable for auditors:

```python
from pathlib import Path
import shutil
import zipfile


def export_compliance_package(
    model_card: ModelCard,
    compliance_report: dict,
    dsar_reports: list[str],
    output_path: str = "compliance_package.zip",
):
    """Package all compliance documentation into a single archive."""
    tmp_dir = Path("compliance_export")
    tmp_dir.mkdir(exist_ok=True)

    # 1. Write Model Card
    with open(tmp_dir / "model_card.json", "w") as f:
        json.dump(asdict(model_card), f, indent=2, default=str)

    # 2. Write Compliance Report
    with open(tmp_dir / "compliance_report.json", "w") as f:
        json.dump(compliance_report, f, indent=2, default=str)

    # 3. Write DSAR reports
    dsar_dir = tmp_dir / "dsar_reports"
    dsar_dir.mkdir(exist_ok=True)
    for report_path in dsar_reports:
        shutil.copy(report_path, dsar_dir)

    # 4. Generate README
    readme = f"""# Compliance Package: {model_card.model_name}

Generated: {datetime.utcnow().isoformat()}
Owner: {model_card.owner}
Compliance Level: {model_card.compliance_level}

## Contents
- model_card.json: Model documentation (GDPR Art. 13)
- compliance_report.json: Full compliance summary (GDPR Art. 35)
- dsar_reports/: Data Subject Access Request responses (GDPR Art. 15)

## Retention
This package should be retained for {365} days.
"""
    with open(tmp_dir / "README.md", "w") as f:
        f.write(readme)

    # 5. Archive
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in tmp_dir.rglob("*"):
            zf.write(file_path, file_path.relative_to(tmp_dir))

    # Cleanup
    shutil.rmtree(tmp_dir)
    print(f"Compliance package exported: {output_path}")
    print(f"Package size: "
          f"{Path(output_path).stat().st_size / 1024:.1f} KB")


# Example: export the full compliance package
# export_compliance_package(
#     model_card, report.generate(), ["dsar_user-1.json"]
# )
```

## Summary

In this exercise, you:
1. Reviewed GDPR requirements and their impact on ML workflows
2. Generated a Model Card from MLflow experiment metadata
3. Built a structured compliance report with data lineage
4. Simulated a Data Subject Access Request (DSAR) workflow
5. Exported a complete compliance package for auditors

---

<div style="display: flex; justify-content: flex-start;">
<a href="../03_audit_logging/" class="md-button">← Previous</a>
</div>
