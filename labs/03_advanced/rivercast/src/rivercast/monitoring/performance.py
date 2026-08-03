"""Delayed model-quality monitoring and the retraining-decision artifact
(PLAN.md Phase 12).

Builds on Phase 9's :mod:`rivercast.processing.delayed_metrics` (the
prediction/observation join and plain MAE/RMSE) to add:

- an Evidently regression report over matured predictions, for the richer
  HTML view operators actually look at;
- rolling-window metrics and error-vs-persistence, reusing the same slicing
  helpers :mod:`rivercast.models.evaluate` already uses offline, so "how we
  slice rising/falling water" is defined once, not twice;
- the retraining-decision artifact (plan §Phase 12 schema). Performance
  degradation is the only condition that requests retraining here; drift is
  reported separately (:mod:`rivercast.monitoring.drift`) and never feeds
  this decision on its own (ADR 0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.core.datasets import Regression
from evidently.presets import RegressionPreset

from rivercast.contracts.predictions import MaturedPrediction
from rivercast.models.evaluate import (
    mae_cm,
    rising_falling_slices,
    rmse_cm,
    water_level_quantile_slices,
)
from rivercast.processing.delayed_metrics import DelayedMetrics, calculate_delayed_metrics


@dataclass(frozen=True)
class SliceDelayedMetric:
    slice_name: str
    slice_value: str
    n: int
    mae_cm: float
    rmse_cm: float


@dataclass(frozen=True)
class RollingPerformanceReport:
    horizon_hours: int
    window_label: str
    checked_at_utc: str
    overall: DelayedMetrics
    error_vs_persistence_mae_cm: float | None
    slices: list[SliceDelayedMetric] = field(default_factory=list)
    evidently_snapshot_json: str | None = None


def _matured_frame(matured_only: list[MaturedPrediction]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "target": [m.actual_cm for m in matured_only],
            "prediction": [m.prediction.prediction_cm for m in matured_only],
            "error_cm": [m.error_cm for m in matured_only],
            "target_time_utc": [m.prediction.target_time_utc for m in matured_only],
        }
    )


def _evidently_regression_snapshot(matured_only: list[MaturedPrediction]) -> str | None:
    """A Regression-preset Evidently report over matured predictions.

    Returns ``None`` (rather than raising) when there are too few matured
    rows for Evidently's regression metrics to be meaningful (e.g. R^2 is
    undefined below two points) -- the plain MAE/RMSE in
    :class:`RollingPerformanceReport.overall` are still reported either way.
    """
    if len(matured_only) < 2:
        return None
    frame = _matured_frame(matured_only)
    data_definition = DataDefinition(
        regression=[Regression(target="target", prediction="prediction")]
    )
    dataset = Dataset.from_pandas(frame, data_definition=data_definition)
    report = Report(metrics=[RegressionPreset()])
    snapshot = report.run(current_data=dataset)
    return str(snapshot.json())


def rolling_performance_report(
    matured: list[MaturedPrediction],
    horizon_hours: int,
    *,
    window_label: str,
    persistence_mae_cm: float | None = None,
    level_now: pd.Series | None = None,
    delta_1h: pd.Series | None = None,
    now_utc: datetime | None = None,
) -> RollingPerformanceReport:
    """Delayed accuracy over one rolling window (e.g. "7d", "30d") for one horizon.

    ``level_now``/``delta_1h`` are optional, index-aligned series (same
    order as the matured predictions actually used) enabling rising/falling
    and level-quantile slices identical to the offline evaluation slices
    (Phase 6); omit them for a report with only the overall metric.
    """
    now = now_utc or datetime.now(UTC)
    horizon_predictions = [m for m in matured if m.prediction.horizon_hours == horizon_hours]
    matured_only = [m for m in horizon_predictions if m.is_matured]
    overall = calculate_delayed_metrics(matured, horizon_hours)

    error_vs_persistence = None
    if persistence_mae_cm is not None and overall.mae_cm is not None and persistence_mae_cm > 0:
        error_vs_persistence = overall.mae_cm - persistence_mae_cm

    slices: list[SliceDelayedMetric] = []
    if matured_only and level_now is not None and delta_1h is not None:
        y_true = np.asarray([m.actual_cm for m in matured_only], dtype=float)
        y_pred = np.asarray([m.prediction.prediction_cm for m in matured_only], dtype=float)
        labelers = {
            "rising_falling": rising_falling_slices(level_now, delta_1h),
            "level_quantile": water_level_quantile_slices(level_now),
        }
        for slice_name, labels in labelers.items():
            frame = pd.DataFrame({"y_true": y_true, "y_pred": y_pred, "slice": labels.to_numpy()})
            for value, group in frame.groupby("slice", observed=True):
                slices.append(
                    SliceDelayedMetric(
                        slice_name=slice_name,
                        slice_value=str(value),
                        n=len(group),
                        mae_cm=mae_cm(group["y_true"].to_numpy(), group["y_pred"].to_numpy()),
                        rmse_cm=rmse_cm(group["y_true"].to_numpy(), group["y_pred"].to_numpy()),
                    )
                )

    return RollingPerformanceReport(
        horizon_hours=horizon_hours,
        window_label=window_label,
        checked_at_utc=now.isoformat(timespec="seconds"),
        overall=overall,
        error_vs_persistence_mae_cm=error_vs_persistence,
        slices=slices,
        evidently_snapshot_json=_evidently_regression_snapshot(matured_only),
    )


@dataclass(frozen=True)
class RetrainingSignal:
    """The retraining-decision artifact (plan §Phase 12 schema)."""

    requested: bool
    reasons: list[str]
    reference_model_version: str | None
    new_labeled_rows: int
    created_at_utc: str


def evaluate_retraining_signal(
    report: RollingPerformanceReport,
    *,
    persistence_mae_cm: float,
    reference_model_version: str | None,
    new_labeled_rows: int,
    performance_degradation_mae_ratio: float,
    min_matured_predictions_for_signal: int,
    now_utc: datetime | None = None,
) -> RetrainingSignal:
    """Decide whether delayed performance alone justifies requesting a retrain.

    Fires only on genuine performance degradation -- ``rolling_mae_cm >=
    persistence_mae_cm * performance_degradation_mae_ratio`` -- never on
    drift (ADR 0003, plan §Phase 12: "Do not retrain solely because feature
    drift is detected"). Withheld (``requested=False``) when there are too
    few matured predictions to trust the rolling metric, even if the ratio
    would otherwise trip -- a noisy small-sample MAE is not evidence.
    """
    now = now_utc or datetime.now(UTC)
    reasons: list[str] = []

    has_enough_data = report.overall.n_matured >= min_matured_predictions_for_signal
    if has_enough_data and report.overall.mae_cm is not None:
        threshold = persistence_mae_cm * performance_degradation_mae_ratio
        if report.overall.mae_cm >= threshold:
            reasons.append(
                f"rolling_mae_degraded: {report.overall.mae_cm:.2f}cm >= "
                f"{threshold:.2f}cm ({performance_degradation_mae_ratio}x persistence)"
            )

    return RetrainingSignal(
        requested=bool(reasons),
        reasons=reasons,
        reference_model_version=reference_model_version,
        new_labeled_rows=new_labeled_rows,
        created_at_utc=now.isoformat(timespec="seconds"),
    )
