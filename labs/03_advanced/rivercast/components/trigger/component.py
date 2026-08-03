"""Trigger component: decide whether a scheduled model-pipeline run should
actually train (PLAN.md Phase 10 "check-training-trigger").

Exits successfully without training when either of two conditions holds:

- fewer than ``thresholds.retraining.min_new_labeled_rows`` labeled rows are
  available for the horizon being considered;
- a training run for the same ``dataset_id`` + horizon already exists in
  MLflow (retraining the identical dataset is a no-op, not a new candidate).

The third plan-mandated skip condition ("data quality fails") is not
re-checked here: ``pipelines/model_pipeline.py`` runs this component only
after ``components.validate`` has already passed on the silver window that
produced the gold dataset (the data-ops pipeline's own gate, PLAN.md
Phase 9) -- re-implementing that check against the gold dataset would be
duplicated logic checking the same underlying data twice.

A skipped run is not a failure: ``status="ok"`` with ``should_train=False``
is the expected, successful outcome of "not enough new data yet" (plan
§Phase 10 acceptance criterion 1: "No new data -> pipeline skips").

Container image: ``rivercast-train`` (Containerfile.train).
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd
from mlflow.client import MlflowClient

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    with_git_commit,
)
from rivercast.contracts.features import DatasetManifest
from rivercast.models.tracking import resolve_tracking_uri
from rivercast.processing import training_rows
from rivercast.storage import zone_key

_LOG = component_logger("trigger")


def run(
    config_path: Path,
    lab_root: Path,
    dataset_short_id: str,
    horizon_hours: int,
) -> ComponentResult:
    """Decide whether to train a candidate for one horizon against one gold dataset."""
    config = load_component_config(config_path)
    store = open_store(config, lab_root)

    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    try:
        dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
        manifest = DatasetManifest.model_validate_json(store.get_bytes(f"{prefix}/manifest.json"))
    except Exception as exc:  # noqa: BLE001 -- any read failure means "cannot evaluate the trigger"
        return ComponentResult(
            component="trigger",
            status="failed",
            metadata={"error": f"could not read gold dataset {dataset_short_id}: {exc}"},
            code_commit=with_git_commit(lab_root),
        )

    label_col = f"target_level_{horizon_hours}h"
    if label_col not in dataset.columns:
        return ComponentResult(
            component="trigger",
            status="failed",
            metadata={"error": f"gold dataset has no label column {label_col!r}"},
            code_commit=with_git_commit(lab_root),
        )

    labeled_row_count = len(training_rows(dataset, [label_col]))
    min_required = config.thresholds.retraining.min_new_labeled_rows
    if labeled_row_count < min_required:
        _LOG.info(
            "trigger: skipping, not enough labeled rows",
            extra={"labeled_row_count": labeled_row_count, "min_required": min_required},
        )
        return ComponentResult(
            component="trigger",
            status="ok",
            metadata={
                "should_train": False,
                "reason": f"only {labeled_row_count} labeled rows, need {min_required}",
                "labeled_row_count": labeled_row_count,
            },
            code_commit=with_git_commit(lab_root),
        )

    registered_model_name = config.mlflow.registered_models.get(str(horizon_hours))
    if registered_model_name is not None:
        tracking_uri = resolve_tracking_uri(config, lab_root)
        client = MlflowClient(tracking_uri=tracking_uri)
        experiment = client.get_experiment_by_name(config.mlflow.experiment)
        if experiment is not None:
            dataset_id = manifest.dataset_id
            existing = client.search_runs(
                [experiment.experiment_id],
                filter_string=(
                    f"params.dataset_id = '{dataset_id}' and "
                    f"params.horizon_hours = '{horizon_hours}'"
                ),
                max_results=1,
            )
            if existing:
                _LOG.info(
                    "trigger: skipping, a run for this dataset already exists",
                    extra={"dataset_id": dataset_id, "existing_run_id": existing[0].info.run_id},
                )
                return ComponentResult(
                    component="trigger",
                    status="ok",
                    metadata={
                        "should_train": False,
                        "reason": f"a training run for dataset {dataset_id} already exists",
                        "existing_run_id": existing[0].info.run_id,
                    },
                    code_commit=with_git_commit(lab_root),
                )

    _LOG.info("trigger: training will proceed", extra={"labeled_row_count": labeled_row_count})
    return ComponentResult(
        component="trigger",
        status="ok",
        metadata={"should_train": True, "labeled_row_count": labeled_row_count},
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Decide whether a model pipeline run should train")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--dataset-id", required=True, help="dataset short id")
    parser.add_argument("--horizon", type=int, required=True)
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        dataset_short_id=args.dataset_id,
        horizon_hours=args.horizon,
    )
    emit(result)


if __name__ == "__main__":
    main()
