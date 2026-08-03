"""Forecast component: issue one prediction from the current champion model
and persist it to the ``predictions`` zone (PLAN.md Phase 9).

Loads the champion model version for one horizon by MLflow alias, scores one
feature row, and writes a :class:`~rivercast.contracts.predictions.PredictionRecord`
to ``predictions/horizon_hours=<h>/issued_at=<ts>-<id>.json`` so a later
pipeline run can join it against the matured observation
(``rivercast.processing.delayed_metrics.join_matured_predictions``) once
``target_time_utc`` has passed.

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
    open_store,
    with_git_commit,
    write_json,
)
from rivercast.contracts.predictions import PredictionRecord
from rivercast.models.registry import get_champion
from rivercast.models.tracking import resolve_tracking_uri
from rivercast.storage import zone_key

_LOG = component_logger("forecast")


def run(
    config_path: Path,
    lab_root: Path,
    horizon_hours: int,
    issue_time: datetime,
    features: dict[str, float],
    created_by_pipeline_run: str | None = None,
    input_snapshot_uri: str | None = None,
) -> ComponentResult:
    """Score one feature row with the current champion for ``horizon_hours``
    and persist the resulting :class:`PredictionRecord`.
    """
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
    issued_at = issue_time.astimezone(UTC)
    target_time = issued_at + timedelta(hours=horizon_hours)
    record = PredictionRecord(
        prediction_id=str(uuid.uuid4()),
        issued_at_utc=issued_at.isoformat(),
        target_time_utc=target_time.isoformat(),
        horizon_hours=horizon_hours,
        target_station_uuid=target.uuid or "",
        prediction_cm=prediction_cm,
        model_name=registered_model_name,
        model_version=str(champion.version),
        model_alias="champion",
        dataset_id=champion.tags.get("dataset_id"),
        feature_version=config.feature_version,
        input_snapshot_uri=input_snapshot_uri,
        created_by_pipeline_run=created_by_pipeline_run,
    )

    store = open_store(config, lab_root)
    prediction_key = zone_key(
        config.storage.zones,
        "predictions",
        f"horizon_hours={horizon_hours}",
        f"issued_at={issued_at.strftime('%Y%m%dT%H%M%SZ')}-{record.prediction_id[:8]}.json",
    )
    write_json(store, prediction_key, record.model_dump())

    _LOG.info(
        "forecast issued",
        extra={
            "horizon_hours": horizon_hours,
            "prediction_cm": prediction_cm,
            "prediction_key": prediction_key,
        },
    )
    return ComponentResult(
        component="forecast",
        status="ok",
        output_keys=[prediction_key],
        metadata=record.model_dump(),
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
    parser.add_argument("--created-by-pipeline-run", default=None)
    parser.add_argument("--input-snapshot-uri", default=None)
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        horizon_hours=args.horizon,
        issue_time=datetime.fromisoformat(args.issue_time).astimezone(UTC),
        features=json.loads(args.features_json),
        created_by_pipeline_run=args.created_by_pipeline_run,
        input_snapshot_uri=args.input_snapshot_uri,
    )
    emit(result)


if __name__ == "__main__":
    main()
