# Exercise 3: Audit Logging

## Objective

In this exercise, you will:
1. Understand audit trail requirements for ML systems
2. Implement an `AuditLogger` for tracking model events
3. Log model prediction events with timestamps and metadata
4. Query audit logs by date range and event type
5. Export audit reports in structured JSON format

## Prerequisites

- Python 3.9+ installed
- A running model serving endpoint (FastAPI or similar)
- Basic understanding of logging and event-driven patterns
- `pandas` installed for log analysis (`pip install pandas`)

!!! tip "MLOps Perspective"
    Security and compliance are foundational to production ML systems. These practices protect models, data, and users while meeting regulatory requirements.

## Step 1: Understanding Audit Trail Requirements

Audit trails in MLOps must capture who did what, when, and with which model version. Regulatory frameworks (SOC 2, GDPR, HIPAA) require:

- **Accountability**: Every prediction and model action must be traceable to a specific user or system
- **Non-repudiation**: Logs must be append-only and tamper-evident
- **Retention**: Logs must be retained for a defined period (e.g., 365 days)
- **Availability**: Logs must be queryable and exportable for investigations

Define the audit event schema:

```python
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any
import json


@dataclass
class AuditEvent:
    event_id: str
    timestamp: str
    event_type: str          # prediction, deployment, retraining, etc.
    model_name: str
    model_version: str
    user_id: str
    input_hash: str          # Hash of input features for reproducibility
    prediction: Any          # The prediction output
    response_time_ms: float
    metadata: dict | None = None
```

## Step 2: Initializing the AuditLogger

Build an append-only audit logger that writes to a JSONL file:

```python
import hashlib
import uuid
from pathlib import Path


class AuditLogger:
    """Append-only audit log for ML model events."""

    def __init__(self, log_path: str = "audit_log.jsonl"):
        self.log_path = Path(log_path)
        # Touch the file to ensure it exists
        self.log_path.touch(exist_ok=True)
        print(f"Audit log initialized: {self.log_path}")

    def _hash_input(self, inputs: dict) -> str:
        """Create a reproducible hash of input features."""
        serialized = json.dumps(inputs, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _generate_event_id(self) -> str:
        """Generate a unique event identifier."""
        return str(uuid.uuid4())

    def log_prediction(
        self,
        model_name: str,
        model_version: str,
        user_id: str,
        inputs: dict,
        prediction: Any,
        response_time_ms: float,
        metadata: dict | None = None,
    ) -> str:
        """Log a model prediction event."""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            timestamp=datetime.utcnow().isoformat(),
            event_type="prediction",
            model_name=model_name,
            model_version=model_version,
            user_id=user_id,
            input_hash=self._hash_input(inputs),
            prediction=prediction,
            response_time_ms=response_time_ms,
            metadata=metadata or {},
        )
        # Append to log file (append-only, never overwrite)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")
        return event.event_id


# Initialize the logger
logger = AuditLogger("ml_audit_log.jsonl")
```

## Step 3: Logging Model Prediction Events

Simulate prediction requests and capture audit events:

```python
import time

# Simulate prediction events
for i in range(5):
    inputs = {
        "season": 1,
        "holiday": 0,
        "temp": 0.75 + (i * 0.05),
        "humidity": 0.6,
    }

    start = time.time()
    # Simulate model inference
    prediction = {"predicted_demand": round(150 + i * 10, 2)}
    elapsed_ms = (time.time() - start) * 1000

    event_id = logger.log_prediction(
        model_name="bike_demand_predictor",
        model_version="v2",
        user_id=f"user-{i % 3 + 1}",
        inputs=inputs,
        prediction=prediction,
        response_time_ms=round(elapsed_ms, 2),
        metadata={"source": "batch-job", "batch_id": f"batch-{i}"},
    )
    print(f"Logged event: {event_id}")
```

## Step 4: Querying Audit Logs

Read and filter audit events by date range or event type:

```python
from datetime import datetime, timedelta
import pandas as pd


class AuditQuery:
    """Query and filter audit logs."""

    def __init__(self, log_path: str = "audit_log.jsonl"):
        self.log_path = Path(log_path)
        self._load()

    def _load(self):
        """Load all events into memory."""
        self.events = []
        if not self.log_path.exists():
            return
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.events.append(json.loads(line))
        print(f"Loaded {len(self.events)} audit events")

    def by_date_range(
        self, start: datetime, end: datetime
    ) -> list[dict]:
        """Filter events within a specific date range."""
        return [
            e for e in self.events
            if start.isoformat() <= e["timestamp"] <= end.isoformat()
        ]

    def by_event_type(self, event_type: str) -> list[dict]:
        """Filter events by type."""
        return [e for e in self.events
                if e["event_type"] == event_type]

    def by_user(self, user_id: str) -> list[dict]:
        """Filter events by user."""
        return [e for e in self.events
                if e["user_id"] == user_id]

    def summary(self) -> dict:
        """Generate a summary of audit events."""
        df = pd.DataFrame(self.events)
        return {
            "total_events": len(df),
            "unique_users": df["user_id"].nunique(),
            "event_types": df["event_type"].value_counts().to_dict(),
            "models_used": df["model_name"].value_counts().to_dict(),
            "avg_response_time_ms": df["response_time_ms"].mean(),
        }


# Query the audit log
query = AuditQuery("ml_audit_log.jsonl")

# Events in the last hour
recent = query.by_date_range(
    datetime.utcnow() - timedelta(hours=1),
    datetime.utcnow(),
)
print(f"Events in last hour: {len(recent)}")

# Events by user
user_events = query.by_user("user-1")
print(f"Events by user-1: {len(user_events)}")

# Summary statistics
summary = query.summary()
print(f"\nAudit Summary:\n{json.dumps(summary, indent=2)}")
```

## Step 5: Exporting Audit Reports

Generate and export structured audit reports in JSON format:

```python
def export_audit_report(
    query: AuditQuery,
    output_path: str,
    report_type: str = "full",
):
    """Export audit data to a JSON report."""
    report = {
        "report_metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": report_type,
            "source_log": str(query.log_path),
            "total_events": len(query.events),
        },
        "events": query.events if report_type == "full" else None,
    }

    if report_type == "summary":
        report["summary"] = query.summary()
    elif report_type == "compliance":
        report["summary"] = query.summary()
        report["compliance_check"] = {
            "retention_days": 365,
            "events_count": len(query.events),
            "has_required_fields": all(
                "user_id" in e and
                "model_version" in e and
                "timestamp" in e
                for e in query.events
            ),
            "tamper_check": "Not implemented - see Appendix A",
        }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report exported: {output_path} ({len(query.events)} events)")


# Export full report
export_audit_report(query, "audit_report_full.json", "full")

# Export compliance report
export_audit_report(query, "audit_report_compliance.json", "compliance")
```

## Summary

In this exercise, you:

1. Defined an audit event schema for ML prediction events
2. Created an append-only `AuditLogger` with tamper-evident design
3. Logged simulated prediction events with full metadata
4. Queried audit logs by date range, user, and event type
5. Exported structured audit reports in JSON format

---

