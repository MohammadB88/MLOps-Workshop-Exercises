"""Register component: register an MLflow run as a new model version
(PLAN.md Phase 7 registry + Phase 8 component contract).

Container image: ``rivercast-train`` (Containerfile.train).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mlflow.client import MlflowClient

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    with_git_commit,
)
from rivercast.models.registry import register_candidate
from rivercast.models.tracking import LoggedRun, resolve_tracking_uri

_LOG = component_logger("register")


def run(
    config_path: Path,
    lab_root: Path,
    run_id: str,
    dataset_id: str,
    horizon_hours: int,
    model_name: str,
) -> ComponentResult:
    """Register the given MLflow run as a version of its horizon's registered model."""
    config = load_component_config(config_path)
    tracking_uri = resolve_tracking_uri(config, lab_root)
    client = MlflowClient(tracking_uri=tracking_uri)

    registered_model_name = config.mlflow.registered_models.get(str(horizon_hours))
    if registered_model_name is None:
        return ComponentResult(
            component="register",
            status="failed",
            metadata={"error": f"no registered_models entry for horizon {horizon_hours}"},
            code_commit=with_git_commit(lab_root),
        )

    logged_run = LoggedRun(
        run_id=run_id,
        experiment_id="",
        dataset_id=dataset_id,
        horizon_hours=horizon_hours,
        model_name=model_name,
    )
    model_version = register_candidate(client, registered_model_name, logged_run)

    _LOG.info(
        "registered model version",
        extra={"registered_model_name": registered_model_name, "version": model_version.version},
    )
    return ComponentResult(
        component="register",
        status="ok",
        metadata={
            "registered_model_name": registered_model_name,
            "model_version": str(model_version.version),
            "run_id": run_id,
        },
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Register an MLflow run as a model version")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--model-name", required=True)
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        run_id=args.run_id,
        dataset_id=args.dataset_id,
        horizon_hours=args.horizon,
        model_name=args.model_name,
    )
    emit(result)


if __name__ == "__main__":
    main()
