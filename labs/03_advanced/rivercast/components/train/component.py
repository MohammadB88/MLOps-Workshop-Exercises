"""Train component: fit a candidate against a gold dataset and log it to
MLflow (PLAN.md Phase 6-7 model code + Phase 8 component contract).

Reads the dataset Parquet + manifest that ``components.transform`` wrote to
gold, temporally splits it, trains one named candidate, evaluates it against
persistence on validation/test, saves the artifact under the ``models`` zone,
and logs the run to MLflow. Registration and promotion are the separate
``components.register`` / ``components.promote`` steps (plan §Phase 8: keep
component outputs small and stable, one step per concern where the concern
already has its own acceptance criteria).

Container image: ``rivercast-train`` (Containerfile.train).
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    with_git_commit,
)
from rivercast.config import RivercastConfig
from rivercast.contracts.features import DatasetManifest
from rivercast.models.baseline import PersistenceModel
from rivercast.models.evaluate import EvaluationReport, evaluate_predictions
from rivercast.models.local_pipeline import TrainRunResult
from rivercast.models.package import save_model
from rivercast.models.split import temporal_split
from rivercast.models.tracking import log_training_run
from rivercast.models.train import ModelName, predict_candidate, train_candidate
from rivercast.processing import training_rows
from rivercast.storage import ObjectStore, zone_key

_LOG = component_logger("train")


def _load_gold_dataset(
    store: ObjectStore, config: RivercastConfig, dataset_short_id: str
) -> tuple[pd.DataFrame, DatasetManifest]:
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    manifest = DatasetManifest.model_validate_json(store.get_bytes(f"{prefix}/manifest.json"))
    frame = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    frame = frame.set_index("issue_time_utc")
    return frame, manifest


def run(
    config_path: Path,
    lab_root: Path,
    dataset_short_id: str,
    horizon_hours: int,
    model_name: ModelName,
    seed: int = 42,
    track_mlflow: bool = True,
) -> ComponentResult:
    """Train one candidate against one gold dataset and save the artifact."""
    config = load_component_config(config_path)
    store = open_store(config, lab_root)

    if horizon_hours not in config.horizons_hours:
        error = f"horizon {horizon_hours} not in configured horizons {config.horizons_hours}"
        return ComponentResult(
            component="train",
            status="failed",
            metadata={"error": error},
            code_commit=with_git_commit(lab_root),
        )

    dataset, manifest = _load_gold_dataset(store, config, dataset_short_id)
    feature_columns = [c for c in dataset.columns if not c.startswith("target_level_")]
    label_col = f"target_level_{horizon_hours}h"
    trainable = training_rows(dataset, [label_col])
    split = temporal_split(trainable, train_fraction=0.7, validation_fraction=0.15)

    persistence = PersistenceModel(f"{config.target_station.lower()}_level_t")
    persistence.fit(split.train[feature_columns], split.train[label_col])
    candidate = train_candidate(
        split.train[feature_columns], split.train[label_col], model_name, horizon_hours, seed=seed
    )

    def _evaluate(part: pd.DataFrame) -> EvaluationReport:
        y_pred = predict_candidate(candidate, part[feature_columns])
        persistence_pred = persistence.predict(part[feature_columns])
        return evaluate_predictions(
            model_name, horizon_hours, part[label_col], y_pred, persistence_pred
        )

    validation_report = _evaluate(split.validation)
    test_report = _evaluate(split.test)

    models_root = Path(lab_root) / "models" / "local"
    model_path = models_root / manifest.short_id / f"{model_name}_h{horizon_hours}.joblib"
    save_model(candidate.estimator, model_path)

    train_result = TrainRunResult(
        dataset_id=manifest.dataset_id,
        horizon_hours=horizon_hours,
        model_name=model_name,
        n_train=len(split.train),
        n_validation=len(split.validation),
        n_test=len(split.test),
        validation_report=validation_report,
        test_report=test_report,
        model_path=model_path,
        candidate=candidate,
        train_features=split.train[feature_columns],
    )

    metadata: dict[str, object] = {
        "dataset_id": manifest.dataset_id,
        "model_name": model_name,
        "horizon_hours": horizon_hours,
        "test_mae_cm": test_report.mae_cm,
        "test_skill_vs_persistence": test_report.skill_vs_persistence,
        "model_path": str(model_path),
    }

    if track_mlflow:
        logged_run = log_training_run(config, lab_root, train_result)
        metadata["mlflow_run_id"] = logged_run.run_id

    _LOG.info(
        "train complete",
        extra={
            "model_name": model_name,
            "horizon_hours": horizon_hours,
            "test_mae_cm": test_report.mae_cm,
        },
    )
    return ComponentResult(
        component="train",
        status="ok",
        output_keys=[str(model_path)],
        metadata=metadata,
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train one candidate against a gold dataset")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument(
        "--dataset-id", required=True, help="dataset short id (gold/training/dataset_id=<id>)"
    )
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--model", choices=["ridge", "hist-gradient-boosting"], required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        dataset_short_id=args.dataset_id,
        horizon_hours=args.horizon,
        model_name=args.model,
        seed=args.seed,
        track_mlflow=not args.no_mlflow,
    )
    emit(result)


if __name__ == "__main__":
    main()
