"""End-to-end local training run: dataset -> split -> train -> evaluate -> save.

Backs the ``rivercast train`` CLI command and the baseline-training notebook.
Phase 6 has no object-store wiring yet (that's Phases 8-9), so the "dataset"
here is materialized on demand from the fixture adapter over the committed
2024-08 overlap window and identified by its manifest's ``dataset_id`` —
the same content-derived ID the object-store version will use later, so
callers and reports do not change shape when storage is added.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from rivercast.config import RivercastConfig
from rivercast.contracts.features import DatasetManifest
from rivercast.models.baseline import PersistenceModel
from rivercast.models.evaluate import EvaluationReport, evaluate_predictions
from rivercast.models.package import save_model
from rivercast.models.split import temporal_split
from rivercast.models.train import ModelName, TrainResult, predict_candidate, train_candidate
from rivercast.processing import (
    assemble_dataset,
    build_features,
    build_labels,
    build_manifest,
    normalize_measurements,
    resample_hourly,
    training_rows,
)
from rivercast.sources.base import parse_measurements
from rivercast.sources.fixture import FixtureGaugeSource

FIXTURE_WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
FIXTURE_WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@dataclass(frozen=True)
class TrainRunResult:
    dataset_id: str
    horizon_hours: int
    model_name: ModelName
    n_train: int
    n_validation: int
    n_test: int
    validation_report: EvaluationReport
    test_report: EvaluationReport
    model_path: Path
    candidate: TrainResult
    train_features: pd.DataFrame


def _require_uuid(name: str, uuid: str | None) -> str:
    if uuid is None:
        raise ValueError(
            f"station {name!r} has no resolved UUID; run the Phase 2 data-viability "
            "spike and pin it in configs/base.yaml before training"
        )
    return uuid


def materialize_fixture_dataset(
    config: RivercastConfig, fixture_dir: Path
) -> tuple[pd.DataFrame, DatasetManifest, list[str]]:
    """Build the leakage-safe dataset from the committed fixtures (fixture mode)."""
    source = FixtureGaugeSource(fixture_dir)
    target = config.station(config.target_station)
    target_uuid = _require_uuid(target.name, target.uuid)
    upstream = [s for s in config.stations if s.name != config.target_station]
    upstream_uuids = [_require_uuid(s.name, s.uuid) for s in upstream]
    prefixes = {_require_uuid(s.name, s.uuid): s.name.lower() for s in config.stations}

    hourly = []
    checksums = set()
    for station in config.stations:
        station_uuid = _require_uuid(station.name, station.uuid)
        raw = source.fetch_raw(station_uuid, "W", FIXTURE_WINDOW_START, FIXTURE_WINDOW_END)
        checksums.add(raw.metadata.sha256)
        normalized = normalize_measurements(
            parse_measurements(raw),
            station.name,
            station.water_body,
            raw.metadata.sha256,
            FIXTURE_WINDOW_END,
        )
        hourly += resample_hourly(
            normalized.observations,
            station_uuid,
            station.name,
            "W",
            FIXTURE_WINDOW_START,
            FIXTURE_WINDOW_END - timedelta(hours=1),
            tolerance_minutes=config.thresholds.data_quality.resample_tolerance_minutes,
        )

    features = build_features(hourly, target_uuid, upstream_uuids, prefixes)
    labels = build_labels(
        hourly,
        target_uuid,
        pd.DatetimeIndex(features.index),
        config.horizons_hours,
        config.thresholds.labels.match_tolerance_minutes,
    )
    dataset = assemble_dataset(features, labels)
    manifest = build_manifest(
        dataset,
        target_station_uuid=target_uuid,
        input_station_uuids=upstream_uuids,
        horizons_hours=config.horizons_hours,
        source_start_utc=FIXTURE_WINDOW_START,
        source_end_utc=FIXTURE_WINDOW_END,
        source_checksums=sorted(checksums),
    )
    return dataset, manifest, list(features.columns)


def run_training(
    config: RivercastConfig,
    fixture_dir: Path,
    horizon_hours: int,
    model_name: ModelName,
    models_dir: Path,
    seed: int = 42,
) -> TrainRunResult:
    """Materialize the dataset, split temporally, train, evaluate, and save."""
    if horizon_hours not in config.horizons_hours:
        raise ValueError(
            f"horizon {horizon_hours} not in configured horizons {config.horizons_hours}"
        )

    dataset, manifest, feature_columns = materialize_fixture_dataset(config, fixture_dir)
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

    model_path = models_dir / manifest.short_id / f"{model_name}_h{horizon_hours}.joblib"
    save_model(candidate.estimator, model_path)

    return TrainRunResult(
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


def report_to_json(result: TrainRunResult) -> str:
    payload = {
        "dataset_id": result.dataset_id,
        "horizon_hours": result.horizon_hours,
        "model_name": result.model_name,
        "n_train": result.n_train,
        "n_validation": result.n_validation,
        "n_test": result.n_test,
        "model_path": str(result.model_path),
        "validation": asdict(result.validation_report),
        "test": asdict(result.test_report),
    }
    return json.dumps(payload, indent=2, default=str)
