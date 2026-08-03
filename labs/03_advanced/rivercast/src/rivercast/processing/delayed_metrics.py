"""Join matured predictions with realized observations and compute delayed
accuracy metrics (PLAN.md Phase 9 pipeline graph: "join-matured-predictions",
"calculate-delayed-metrics").

A prediction "matures" once its ``target_time_utc`` has actually happened
and a real hourly observation exists for it. This module never fabricates a
missing observation (rule 13): an unmatured or missing-data prediction joins
to ``actual_cm=None`` and is excluded from the metrics, not zero-filled.

Full Evidently-based drift/performance monitoring (rolling windows, feature
drift, Evidently reports) is Phase 12's ``rivercast.monitoring`` package;
this module only builds the join and the plain MAE/RMSE metrics the Phase 9
pipeline's ``calculate-delayed-metrics`` step needs, over data that already
exists (predictions + hourly observations) rather than data that doesn't
(drift baselines, prior monitoring runs).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rivercast.contracts.hourly import HourlyObservation
from rivercast.contracts.predictions import MaturedPrediction, PredictionRecord


def join_matured_predictions(
    predictions: list[PredictionRecord],
    hourly: list[HourlyObservation],
    now_utc: datetime | None = None,
) -> list[MaturedPrediction]:
    """Join each prediction to the hourly observation at its ``target_time_utc``.

    A prediction only matures once ``target_time_utc`` is at or before
    ``now_utc`` *and* a non-missing hourly observation exists at that exact
    hour for the target station; otherwise ``actual_cm``/``error_cm`` are
    ``None``. Predictions are never dropped here -- unmatured ones pass
    through so a caller can distinguish "not yet due" from "matured but no
    data" if needed.
    """
    now = now_utc or datetime.now(UTC)
    by_station_hour: dict[tuple[str, datetime], float] = {
        (obs.station_uuid, obs.hour_utc): obs.value
        for obs in hourly
        if not obs.is_missing and obs.value is not None
    }

    matured: list[MaturedPrediction] = []
    for prediction in predictions:
        target_time = datetime.fromisoformat(prediction.target_time_utc)
        actual_cm: float | None = None
        if target_time <= now:
            actual_cm = by_station_hour.get((prediction.target_station_uuid, target_time))

        error_cm = None if actual_cm is None else actual_cm - prediction.prediction_cm
        matured.append(
            MaturedPrediction(
                prediction=prediction,
                actual_cm=actual_cm,
                error_cm=error_cm,
                matured_at_utc=now.isoformat(timespec="seconds"),
            )
        )
    return matured


@dataclass(frozen=True)
class DelayedMetrics:
    horizon_hours: int
    n_matured: int
    n_total: int
    mae_cm: float | None
    rmse_cm: float | None


def calculate_delayed_metrics(
    matured: list[MaturedPrediction], horizon_hours: int
) -> DelayedMetrics:
    """MAE/RMSE over matured predictions for one horizon.

    Unmatured predictions are counted in ``n_total`` but excluded from the
    metrics themselves; ``mae_cm``/``rmse_cm`` are ``None`` when nothing has
    matured yet, never a misleading ``0.0``.
    """
    horizon_predictions = [m for m in matured if m.prediction.horizon_hours == horizon_hours]
    matured_only = [m for m in horizon_predictions if m.is_matured]

    if not matured_only:
        return DelayedMetrics(
            horizon_hours=horizon_hours,
            n_matured=0,
            n_total=len(horizon_predictions),
            mae_cm=None,
            rmse_cm=None,
        )

    errors = [abs(m.error_cm) for m in matured_only if m.error_cm is not None]
    squared_errors = [e * e for e in errors]
    mae = sum(errors) / len(errors)
    rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5
    return DelayedMetrics(
        horizon_hours=horizon_hours,
        n_matured=len(matured_only),
        n_total=len(horizon_predictions),
        mae_cm=mae,
        rmse_cm=rmse,
    )
