"""Report object-store keys and MLflow runs eligible for retention cleanup
(PLAN.md Phase 15 "object-store lifecycle policy" / "retention policy for
raw and prediction data" / "artifact retention").

Report-only by design -- see ``rivercast.retention`` module docstring for
why this never deletes anything itself. Run from the lab root:

    python -m scripts.retention_report --config configs/local.yaml \\
        --bronze-retention-days 90 --predictions-retention-days 180

Prints one JSON object per zone/section to stdout.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import mlflow
from components.common import open_store
from mlflow.client import MlflowClient

from rivercast.config import load_config
from rivercast.models.tracking import resolve_tracking_uri
from rivercast.retention import build_retention_report

_LAB_ROOT = Path(__file__).resolve().parents[1]


def report_mlflow_runs_older_than(
    config_path: Path, lab_root: Path, retention_days: int
) -> dict[str, object]:
    """List finished MLflow runs older than ``retention_days`` that are not
    the current ``champion``/``challenger`` for any registered model --
    those two aliases must never be reported as cleanup candidates, even if
    old, since a champion rollback (``promote``) can re-point to an older
    run at any time (rule 14: a deployment failure must not move champion,
    which implies past champions stay resolvable).
    """
    config = load_config(config_path)
    tracking_uri = resolve_tracking_uri(config, lab_root)
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    protected_run_ids: set[str] = set()
    for model_name in config.mlflow.registered_models.values():
        for alias in ("champion", "challenger"):
            try:
                version = client.get_model_version_by_alias(model_name, alias)
            except mlflow.exceptions.MlflowException:
                continue
            protected_run_ids.add(version.run_id)

    experiment = client.get_experiment_by_name(config.mlflow.experiment)
    if experiment is None:
        return {"experiment": config.mlflow.experiment, "candidates": [], "total_runs": 0}

    cutoff_ms = int(
        (mlflow.utils.time.get_current_time_millis() / 1000 - retention_days * 86400) * 1000
    )
    all_runs = client.search_runs([experiment.experiment_id], max_results=50_000)
    candidates = [
        {"run_id": run.info.run_id, "start_time_ms": run.info.start_time}
        for run in all_runs
        if run.info.run_id not in protected_run_ids and run.info.start_time < cutoff_ms
    ]
    return {
        "experiment": config.mlflow.experiment,
        "retention_days": retention_days,
        "total_runs": len(all_runs),
        "protected_run_ids": sorted(protected_run_ids),
        "candidates": sorted(candidates, key=lambda c: c["run_id"]),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Report object-store keys and MLflow runs eligible for retention cleanup"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", type=Path, default=_LAB_ROOT)
    parser.add_argument("--bronze-retention-days", type=int, default=90)
    parser.add_argument("--predictions-retention-days", type=int, default=180)
    parser.add_argument("--mlflow-retention-days", type=int, default=180)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    store = open_store(config, args.lab_root)

    bronze_report = build_retention_report(
        store,
        "bronze",
        config.storage.zones.bronze,
        retention_days=args.bronze_retention_days,
    )
    predictions_report = build_retention_report(
        store,
        "predictions",
        config.storage.zones.predictions,
        retention_days=args.predictions_retention_days,
    )
    mlflow_report = report_mlflow_runs_older_than(
        args.config, args.lab_root, args.mlflow_retention_days
    )

    print(
        json.dumps(
            {
                "bronze": asdict(bronze_report),
                "predictions": asdict(predictions_report),
                "mlflow_runs": mlflow_report,
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
