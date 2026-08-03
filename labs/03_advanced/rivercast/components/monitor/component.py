"""Monitor component: data-freshness/coverage summary (Phase 8/9), extended
with delayed model-quality monitoring, feature drift, and the
retraining-decision artifact (PLAN.md Phase 12).

The Phase 8/9 data-monitoring summary (freshness, row count, missingness,
station coverage) always runs. The Phase 12 additions -- delayed
performance, drift, and the retraining signal -- are best-effort per
horizon: they need matured predictions and a champion with a logged
evaluation to be meaningful, neither of which exists on a fresh fixture
window, so this component still succeeds and reports plainly when they're
unavailable (plan §Phase 12 acceptance: "Reports work with no labels and
with delayed labels"). Drift alone never requests retraining (ADR 0003);
only genuine performance degradation does, computed in
:mod:`rivercast.monitoring.performance`.

Container image: ``rivercast-ops`` (Containerfile.ops).
"""

from __future__ import annotations

import argparse
import io
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from mlflow.client import MlflowClient

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    read_json,
    with_git_commit,
    write_json,
)
from rivercast.config import RivercastConfig
from rivercast.contracts.hourly import HourlyObservation
from rivercast.contracts.predictions import MaturedPrediction, PredictionRecord
from rivercast.models.registry import champion_test_report, get_champion
from rivercast.models.tracking import resolve_tracking_uri
from rivercast.monitoring.drift import run_drift_report
from rivercast.monitoring.performance import evaluate_retraining_signal, rolling_performance_report
from rivercast.processing.delayed_metrics import join_matured_predictions
from rivercast.storage import ObjectStore, zone_key

_LOG = component_logger("monitor")


def _load_predictions(
    store: ObjectStore, config: RivercastConfig, horizon_hours: int
) -> list[PredictionRecord]:
    prefix = zone_key(config.storage.zones, "predictions", f"horizon_hours={horizon_hours}")
    return [
        PredictionRecord.model_validate(read_json(store, key))
        for key in store.list_keys(f"{prefix}/")
    ]


def _load_gold_dataset(
    store: ObjectStore, config: RivercastConfig, dataset_short_id: str
) -> pd.DataFrame:
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    return pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))


def _delayed_monitoring_for_horizon(
    config: RivercastConfig,
    lab_root: Path,
    store: ObjectStore,
    matured: list[MaturedPrediction],
    horizon_hours: int,
    dataset_short_id: str | None,
    now: datetime,
) -> dict[str, object]:
    """Best-effort delayed performance + drift + retraining signal for one
    horizon. Never raises -- a missing champion, empty predictions, or no
    gold dataset yet are reported as absent sections rather than failing
    the whole monitoring run.
    """
    section: dict[str, object] = {
        "horizon_hours": horizon_hours,
        "performance": None,
        "drift": None,
        "retraining_signal": None,
    }

    registered_model_name = config.mlflow.registered_models.get(str(horizon_hours))
    if registered_model_name is None:
        return section

    tracking_uri = resolve_tracking_uri(config, lab_root)
    client = MlflowClient(tracking_uri=tracking_uri)
    champion = get_champion(client, registered_model_name)
    if champion is None:
        return section

    test_report = champion_test_report(client, champion)
    persistence_mae_cm = test_report.persistence_mae_cm if test_report is not None else None

    performance_report = rolling_performance_report(
        matured,
        horizon_hours,
        window_label="all_matured",
        persistence_mae_cm=persistence_mae_cm,
        now_utc=now,
    )
    section["performance"] = {
        "window_label": performance_report.window_label,
        "checked_at_utc": performance_report.checked_at_utc,
        "n_matured": performance_report.overall.n_matured,
        "n_total": performance_report.overall.n_total,
        "mae_cm": performance_report.overall.mae_cm,
        "rmse_cm": performance_report.overall.rmse_cm,
        "error_vs_persistence_mae_cm": performance_report.error_vs_persistence_mae_cm,
    }

    if persistence_mae_cm is not None:
        signal = evaluate_retraining_signal(
            performance_report,
            persistence_mae_cm=persistence_mae_cm,
            reference_model_version=str(champion.version),
            new_labeled_rows=performance_report.overall.n_matured,
            performance_degradation_mae_ratio=(
                config.thresholds.monitoring.performance_degradation_mae_ratio
            ),
            min_matured_predictions_for_signal=(
                config.thresholds.monitoring.min_matured_predictions_for_signal
            ),
            now_utc=now,
        )
        section["retraining_signal"] = asdict(signal)

    if dataset_short_id is not None:
        dataset = _load_gold_dataset(store, config, dataset_short_id)
        feature_columns = [
            c
            for c in dataset.columns
            if not c.startswith("target_level_") and c != "issue_time_utc"
        ]
        filled = dataset[feature_columns].fillna(0.0)
        n = len(filled)
        if n >= 4:  # need a non-trivial split on both sides to compare
            midpoint = n // 2
            reference, current = filled.iloc[:midpoint], filled.iloc[midpoint:]
            drift_report = run_drift_report(
                reference,
                current,
                feature_columns,
                warning_threshold=config.thresholds.monitoring.drift_share_warning_threshold,
                now_utc=now,
            )
            section["drift"] = {
                "checked_at_utc": drift_report.checked_at_utc,
                "reference_row_count": drift_report.reference_row_count,
                "current_row_count": drift_report.current_row_count,
                "drifted_share": drift_report.drifted_share,
                "is_warning": drift_report.is_warning,
            }

    return section


def run(
    config_path: Path,
    lab_root: Path,
    silver_key: str,
    dataset_short_id: str | None = None,
    now_utc: datetime | None = None,
) -> ComponentResult:
    """Summarize freshness, coverage, and missingness for one silver window,
    plus (best-effort, per configured horizon) delayed performance, drift,
    and the retraining-decision signal.
    """
    config = load_component_config(config_path)
    store = open_store(config, lab_root)
    now = now_utc or datetime.now(UTC)

    raw_rows = read_json(store, silver_key)
    hourly = [HourlyObservation.model_validate(row) for row in raw_rows]

    required_uuids = {s.uuid for s in config.stations if s.uuid is not None}
    by_station: dict[str, list[HourlyObservation]] = {}
    for obs in hourly:
        by_station.setdefault(obs.station_uuid, []).append(obs)

    station_summaries = {}
    for station_uuid, rows in by_station.items():
        latest_present = max((r.hour_utc for r in rows if not r.is_missing), default=None)
        staleness_minutes = (
            (now - latest_present).total_seconds() / 60.0 if latest_present is not None else None
        )
        station_summaries[station_uuid] = {
            "row_count": len(rows),
            "missing_count": sum(1 for r in rows if r.is_missing),
            "latest_present_hour_utc": latest_present.isoformat() if latest_present else None,
            "staleness_minutes": staleness_minutes,
        }

    missing_stations = sorted(required_uuids - by_station.keys())

    target = config.station(config.target_station)
    delayed_by_horizon: list[dict[str, object]] = []
    if target.uuid is not None:
        for horizon_hours in config.horizons_hours:
            predictions = _load_predictions(store, config, horizon_hours)
            matured = join_matured_predictions(predictions, hourly, now_utc=now)
            delayed_by_horizon.append(
                _delayed_monitoring_for_horizon(
                    config, lab_root, store, matured, horizon_hours, dataset_short_id, now
                )
            )

    summary = {
        "checked_at_utc": now.isoformat(timespec="seconds"),
        "silver_key": silver_key,
        "row_count": len(hourly),
        "missing_station_count": len(missing_stations),
        "missing_stations": missing_stations,
        "by_station": station_summaries,
        "delayed_by_horizon": delayed_by_horizon,
    }

    report_key = zone_key(
        config.storage.zones,
        "reports",
        "monitoring",
        f"{silver_key.rsplit('/', 1)[-1].removesuffix('.json')}_monitor.json",
    )
    write_json(store, report_key, summary, overwrite=True)

    any_retraining_requested = any(
        h["retraining_signal"] is not None and h["retraining_signal"]["requested"]  # type: ignore[index]
        for h in delayed_by_horizon
    )

    _LOG.info(
        "monitor summary written",
        extra={
            "row_count": summary["row_count"],
            "missing_station_count": len(missing_stations),
            "any_retraining_requested": any_retraining_requested,
        },
    )
    return ComponentResult(
        component="monitor",
        status="ok",
        output_keys=[report_key],
        metadata={
            "row_count": summary["row_count"],
            "missing_station_count": len(missing_stations),
            "any_retraining_requested": any_retraining_requested,
        },
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize freshness/coverage, delayed performance, and drift for a silver window"
        )
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--silver-key", required=True)
    parser.add_argument(
        "--dataset-id", default=None, help="gold dataset short id, for drift reports"
    )
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        silver_key=args.silver_key,
        dataset_short_id=args.dataset_id,
    )
    emit(result)


if __name__ == "__main__":
    main()
