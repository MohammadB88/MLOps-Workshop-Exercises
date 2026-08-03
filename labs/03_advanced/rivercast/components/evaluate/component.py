"""Evaluate component: score a saved model artifact against a gold dataset
split (PLAN.md Phase 6 evaluation + Phase 8 component contract).

Separate from ``components.train`` so an already-trained/registered artifact
(e.g. the current champion) can be re-evaluated against a new dataset split
without retraining — the shape the Phase 10 model-pipeline graph needs
(``train-candidate`` and ``evaluate-and-slice`` are distinct DAG nodes).

Container image: ``rivercast-train`` (Containerfile.train).
"""

from __future__ import annotations

import argparse
import io
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import pandas as pd

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    with_git_commit,
    write_json,
)
from rivercast.contracts.features import DatasetManifest
from rivercast.models.baseline import PersistenceModel
from rivercast.models.evaluate import evaluate_predictions
from rivercast.models.package import load_model, predict
from rivercast.models.split import temporal_split
from rivercast.processing import training_rows
from rivercast.storage import zone_key

_LOG = component_logger("evaluate")


def run(
    config_path: Path,
    lab_root: Path,
    dataset_short_id: str,
    horizon_hours: int,
    model_path: Path,
    model_name: str,
    split_name: Literal["train", "validation", "test"] = "test",
) -> ComponentResult:
    """Evaluate a saved model artifact against one split of a gold dataset."""
    config = load_component_config(config_path)
    store = open_store(config, lab_root)

    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    manifest = DatasetManifest.model_validate_json(store.get_bytes(f"{prefix}/manifest.json"))
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    dataset = dataset.set_index("issue_time_utc")

    feature_columns = [c for c in dataset.columns if not c.startswith("target_level_")]
    label_col = f"target_level_{horizon_hours}h"
    trainable = training_rows(dataset, [label_col])
    split = temporal_split(trainable, train_fraction=0.7, validation_fraction=0.15)
    splits = {"train": split.train, "validation": split.validation, "test": split.test}
    part = splits[split_name]
    if len(part) == 0:
        return ComponentResult(
            component="evaluate",
            status="failed",
            metadata={"error": f"'{split_name}' split is empty for this dataset"},
            code_commit=with_git_commit(lab_root),
        )

    model = load_model(model_path)
    persistence = PersistenceModel(f"{config.target_station.lower()}_level_t")
    persistence.fit(split.train[feature_columns], split.train[label_col])

    y_pred = predict(model, part[feature_columns])
    persistence_pred = persistence.predict(part[feature_columns])
    report = evaluate_predictions(
        model_name, horizon_hours, part[label_col], y_pred, persistence_pred
    )

    report_key = zone_key(
        config.storage.zones,
        "reports",
        "evaluation",
        f"dataset_id={manifest.short_id}",
        f"{model_name}_h{horizon_hours}_{split_name}.json",
    )
    write_json(store, report_key, asdict(report), overwrite=True)

    _LOG.info(
        "evaluate complete",
        extra={"model_name": model_name, "horizon_hours": horizon_hours, "mae_cm": report.mae_cm},
    )
    return ComponentResult(
        component="evaluate",
        status="ok",
        output_keys=[report_key],
        metadata={
            "dataset_id": manifest.dataset_id,
            "mae_cm": report.mae_cm,
            "rmse_cm": report.rmse_cm,
            "skill_vs_persistence": report.skill_vs_persistence,
        },
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate a saved model artifact")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"], default="test")
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        dataset_short_id=args.dataset_id,
        horizon_hours=args.horizon,
        model_path=args.model_path,
        model_name=args.model_name,
        split_name=args.split,
    )
    emit(result)


if __name__ == "__main__":
    main()
