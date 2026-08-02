"""MLflow experiment tracking for training runs (PLAN.md Phase 7).

Wraps a completed :class:`~rivercast.models.local_pipeline.TrainRunResult` and
logs everything the plan requires for one MLflow run: parameters, metrics,
slice metrics, feature list, dataset manifest, evaluation summary, model
signature, input example, Git commit, image digest, station UUIDs, horizon,
and the serialized model itself. Notebooks and the CLI call
:func:`log_training_run`; no MLflow calls belong outside this module or
``registry.py`` (CLAUDE.md rule 17).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import mlflow
from mlflow.models import infer_signature

from rivercast.config import RivercastConfig
from rivercast.gitinfo import current_commit
from rivercast.models.evaluate import SliceMetric
from rivercast.models.local_pipeline import TrainRunResult

IMAGE_DIGEST_ENV_VAR = "RIVERCAST_IMAGE_DIGEST"


@dataclass(frozen=True)
class LoggedRun:
    run_id: str
    experiment_id: str
    dataset_id: str
    horizon_hours: int
    model_name: str


def resolve_tracking_uri(config: RivercastConfig, lab_root: Path) -> str:
    """Env var takes priority; otherwise fall back to the configured default.

    A relative ``sqlite:///...`` default is resolved against
    ``storage.root`` (under ``lab_root`` if relative) so fixture-mode runs
    keep their tracking store next to the rest of the local artifacts.
    """
    env_uri = os.environ.get(config.mlflow.tracking_uri_env_var)
    if env_uri:
        return env_uri
    default = config.mlflow.tracking_uri_default
    if default is None:
        raise ValueError(
            f"{config.mlflow.tracking_uri_env_var} is not set and mlflow.tracking_uri_default "
            "is not configured; set the environment variable or add a default in configs/base.yaml"
        )
    if default.startswith("sqlite:///") and not default.startswith("sqlite:////"):
        # Relative sqlite path: anchor it under storage.root, not the CWD.
        relative_path = default.removeprefix("sqlite:///")
        storage_root = Path(config.storage.root)
        if not storage_root.is_absolute():
            storage_root = lab_root / storage_root
        db_path = (storage_root / relative_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.as_posix()}"
    return default


def _slice_metrics_dict(report_name: str, slices: list[SliceMetric]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for slice_metric in slices:
        key = f"{report_name}_{slice_metric.slice_name}_{slice_metric.slice_value}"
        metrics[f"{key}_mae_cm"] = slice_metric.mae_cm
        metrics[f"{key}_rmse_cm"] = slice_metric.rmse_cm
        metrics[f"{key}_n"] = float(slice_metric.n)
    return metrics


def log_training_run(
    config: RivercastConfig,
    lab_root: Path,
    result: TrainRunResult,
) -> LoggedRun:
    """Log one training run (params, metrics, artifacts, model) to MLflow.

    Does not register or promote anything — that is
    ``registry.register_candidate`` / ``registry.promote``, kept separate so
    a run can be inspected before any registry state changes.
    """
    candidate = result.candidate
    train_features = result.train_features
    tracking_uri = resolve_tracking_uri(config, lab_root)
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(config.mlflow.experiment)

    station_uuids = {s.name: s.uuid for s in config.stations}
    run_name = f"{result.model_name}_h{result.horizon_hours}h_{result.dataset_id[7:19]}"

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "model_name": result.model_name,
                "horizon_hours": result.horizon_hours,
                "seed": candidate.seed,
                "dataset_id": result.dataset_id,
                "n_train": result.n_train,
                "n_validation": result.n_validation,
                "n_test": result.n_test,
                "target_station": config.target_station,
                **{f"hp_{k}": v for k, v in candidate.params.items()},
            }
        )

        metrics = {
            "validation_mae_cm": result.validation_report.mae_cm,
            "validation_rmse_cm": result.validation_report.rmse_cm,
            "validation_skill_vs_persistence": result.validation_report.skill_vs_persistence,
            "test_mae_cm": result.test_report.mae_cm,
            "test_rmse_cm": result.test_report.rmse_cm,
            "test_skill_vs_persistence": result.test_report.skill_vs_persistence,
            "test_persistence_mae_cm": result.test_report.persistence_mae_cm,
        }
        metrics.update(_slice_metrics_dict("validation", result.validation_report.slices))
        metrics.update(_slice_metrics_dict("test", result.test_report.slices))
        mlflow.log_metrics(metrics)

        mlflow.set_tags(
            {
                "validation_status": "pending",
                "dataset_id": result.dataset_id,
                "horizon_hours": str(result.horizon_hours),
                "deployment_status": "not_deployed",
                "git_commit": current_commit(lab_root) or "unknown",
                "image_digest": os.environ.get(IMAGE_DIGEST_ENV_VAR, "unknown"),
                "target_station_uuid": station_uuids.get(config.target_station) or "unknown",
                "input_station_uuids": ",".join(
                    sorted(
                        uuid
                        for name, uuid in station_uuids.items()
                        if uuid and name != config.target_station
                    )
                ),
            }
        )

        mlflow.log_dict(
            {
                "dataset_id": result.dataset_id,
                "horizon_hours": result.horizon_hours,
                "feature_columns": candidate.feature_columns,
                "n_train": result.n_train,
                "n_validation": result.n_validation,
                "n_test": result.n_test,
            },
            "dataset_manifest.json",
        )
        mlflow.log_dict({"columns": candidate.feature_columns}, "feature_list.json")

        input_example = train_features.head(3)
        signature = infer_signature(input_example, candidate.estimator.predict(input_example))
        # cloudpickle, not the mlflow 3.x default of skops: skops's load-time
        # trust audit rejects numpy.dtype (used internally by our sklearn
        # Pipelines) unless explicitly allow-listed, and joblib/pickle is
        # already this project's serialization format for local artifacts
        # (models/package.py) -- one format, one trust model.
        mlflow.sklearn.log_model(
            candidate.estimator,
            name="model",
            signature=signature,
            input_example=input_example,
            serialization_format="cloudpickle",
        )

        run_id = run.info.run_id
        experiment_id = run.info.experiment_id

    return LoggedRun(
        run_id=run_id,
        experiment_id=experiment_id,
        dataset_id=result.dataset_id,
        horizon_hours=result.horizon_hours,
        model_name=result.model_name,
    )
