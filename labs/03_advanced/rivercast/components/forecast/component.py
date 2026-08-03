"""Forecast component: issue one prediction from the current champion model
(PLAN.md Phase 9 prediction-record shape, called early per Phase 8's
component contract).

Loads the champion model version for one horizon by MLflow alias and scores
one feature row, producing a record shaped exactly like the Phase 9
prediction-record schema (``prediction_id``, ``issued_at_utc``,
``target_time_utc``, ...). This component does *not* persist that record to
the ``predictions`` object-store zone or define ``contracts/predictions.py``
— that lineage/versioning contract, and the scheduled/hourly calling
context, are Phase 9's job (``rivercast-data-ops`` pipeline); building it
ahead of the pipeline that owns it would be speculative. What Phase 8 needs
from this component is proven now: it loads a champion by alias and scores a
feature row as a normal, testable Python function.

Container image: ``rivercast-serving`` (Containerfile.serving).
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from mlflow.client import MlflowClient

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    with_git_commit,
)
from rivercast.models.registry import get_champion
from rivercast.models.tracking import resolve_tracking_uri

_LOG = component_logger("forecast")


def run(
    config_path: Path,
    lab_root: Path,
    horizon_hours: int,
    issue_time: datetime,
    features: dict[str, float],
    created_by_pipeline_run: str | None = None,
) -> ComponentResult:
    """Score one feature row with the current champion for ``horizon_hours``."""
    config = load_component_config(config_path)
    registered_model_name = config.mlflow.registered_models.get(str(horizon_hours))
    if registered_model_name is None:
        return ComponentResult(
            component="forecast",
            status="failed",
            metadata={"error": f"no registered_models entry for horizon {horizon_hours}"},
            code_commit=with_git_commit(lab_root),
        )

    tracking_uri = resolve_tracking_uri(config, lab_root)
    client = MlflowClient(tracking_uri=tracking_uri)
    champion = get_champion(client, registered_model_name)
    if champion is None:
        return ComponentResult(
            component="forecast",
            status="failed",
            metadata={"error": f"no champion set for {registered_model_name} yet"},
            code_commit=with_git_commit(lab_root),
        )

    mlflow.set_tracking_uri(tracking_uri)
    # runs:/<run_id>/model, not models:/<name>@champion: see
    # components.common.model_run_uri for why the models:/ URI form is
    # unsafe to load from on Windows with the currently pinned mlflow.
    model = mlflow.pyfunc.load_model(f"runs:/{champion.run_id}/model")
    # predict() may return a pandas Series or a bare numpy array depending
    # on the model flavor; normalize before indexing.
    prediction_cm = float(np.asarray(model.predict(_as_frame(features)))[0])

    target = config.station(config.target_station)
    record = {
        "prediction_id": str(uuid.uuid4()),
        "issued_at_utc": issue_time.astimezone(UTC).isoformat(),
        "target_time_utc": (issue_time + timedelta(hours=horizon_hours))
        .astimezone(UTC)
        .isoformat(),
        "horizon_hours": horizon_hours,
        "target_station_uuid": target.uuid,
        "prediction_cm": prediction_cm,
        "model_name": registered_model_name,
        "model_version": str(champion.version),
        "model_alias": "champion",
        "dataset_id": champion.tags.get("dataset_id"),
        "feature_version": config.feature_version,
        "created_by_pipeline_run": created_by_pipeline_run,
    }

    _LOG.info(
        "forecast issued",
        extra={"horizon_hours": horizon_hours, "prediction_cm": prediction_cm},
    )
    return ComponentResult(
        component="forecast",
        status="ok",
        metadata=record,
        code_commit=with_git_commit(lab_root),
    )


def _as_frame(features: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame([features])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Issue one prediction from the champion model")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--issue-time", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--features-json", required=True, help="JSON object of feature values")
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        horizon_hours=args.horizon,
        issue_time=datetime.fromisoformat(args.issue_time).astimezone(UTC),
        features=json.loads(args.features_json),
    )
    emit(result)


if __name__ == "__main__":
    main()
