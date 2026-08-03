"""Tests for join_matured_predictions / calculate_delayed_metrics (Phase 9)."""

from __future__ import annotations

from datetime import UTC, datetime

from rivercast.contracts.hourly import HourlyObservation
from rivercast.contracts.predictions import PredictionRecord
from rivercast.processing.delayed_metrics import (
    calculate_delayed_metrics,
    join_matured_predictions,
)

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"


def _prediction(
    horizon: int, target_hour: int, prediction_cm: float, prediction_id: str = "p1"
) -> PredictionRecord:
    return PredictionRecord(
        prediction_id=prediction_id,
        issued_at_utc=datetime(2024, 8, 1, target_hour - horizon, tzinfo=UTC).isoformat(),
        target_time_utc=datetime(2024, 8, 1, target_hour, tzinfo=UTC).isoformat(),
        horizon_hours=horizon,
        target_station_uuid=STATION,
        prediction_cm=prediction_cm,
        model_name="rivercast-kaub-6h",
        model_version="1",
        model_alias="champion",
        dataset_id="sha256:abc",
        feature_version=1,
    )


def _hourly(hour: int, value: float | None, missing: bool = False) -> HourlyObservation:
    return HourlyObservation(
        station_uuid=STATION,
        station_name="KAUB",
        parameter="W",
        hour_utc=datetime(2024, 8, 1, hour, tzinfo=UTC),
        value=value,
        is_missing=missing,
    )


def test_join_matures_a_prediction_with_a_real_observation() -> None:
    prediction = _prediction(horizon=6, target_hour=10, prediction_cm=98.0)
    hourly = [_hourly(10, value=100.0)]
    now = datetime(2024, 8, 1, 11, tzinfo=UTC)  # after target_time

    [matured] = join_matured_predictions([prediction], hourly, now_utc=now)

    assert matured.is_matured
    assert matured.actual_cm == 100.0
    assert matured.error_cm == 2.0  # actual - prediction


def test_join_leaves_future_predictions_unmatured() -> None:
    prediction = _prediction(horizon=6, target_hour=10, prediction_cm=98.0)
    hourly = [_hourly(10, value=100.0)]
    now = datetime(2024, 8, 1, 9, tzinfo=UTC)  # before target_time

    [matured] = join_matured_predictions([prediction], hourly, now_utc=now)

    assert not matured.is_matured
    assert matured.actual_cm is None
    assert matured.error_cm is None


def test_join_does_not_fabricate_a_missing_observation() -> None:
    """target_time_utc has passed but the hourly grid marks that hour
    missing -- the prediction must NOT be silently matured against a
    fabricated value (rule 13: fail closed / never fabricate).
    """
    prediction = _prediction(horizon=6, target_hour=10, prediction_cm=98.0)
    hourly = [_hourly(10, value=None, missing=True)]
    now = datetime(2024, 8, 1, 11, tzinfo=UTC)

    [matured] = join_matured_predictions([prediction], hourly, now_utc=now)

    assert not matured.is_matured
    assert matured.actual_cm is None


def test_join_does_not_match_across_stations() -> None:
    prediction = _prediction(horizon=6, target_hour=10, prediction_cm=98.0)
    other_station_obs = HourlyObservation(
        station_uuid="a37a9aa3-45e9-4d90-9df6-109f3a28a5af",
        station_name="MAINZ",
        parameter="W",
        hour_utc=datetime(2024, 8, 1, 10, tzinfo=UTC),
        value=100.0,
        is_missing=False,
    )
    now = datetime(2024, 8, 1, 11, tzinfo=UTC)

    [matured] = join_matured_predictions([prediction], [other_station_obs], now_utc=now)

    assert not matured.is_matured


def test_calculate_delayed_metrics_over_multiple_matured_predictions() -> None:
    predictions = [
        _prediction(6, 10, 98.0, "p1"),
        _prediction(6, 11, 105.0, "p2"),
    ]
    hourly = [_hourly(10, value=100.0), _hourly(11, value=100.0)]
    now = datetime(2024, 8, 1, 12, tzinfo=UTC)

    matured = join_matured_predictions(predictions, hourly, now_utc=now)
    metrics = calculate_delayed_metrics(matured, horizon_hours=6)

    assert metrics.n_matured == 2
    assert metrics.n_total == 2
    # errors: |100-98|=2, |100-105|=5 -> mae = 3.5
    assert metrics.mae_cm == 3.5
    assert metrics.rmse_cm is not None


def test_calculate_delayed_metrics_returns_none_when_nothing_matured() -> None:
    prediction = _prediction(horizon=6, target_hour=10, prediction_cm=98.0)
    now = datetime(2024, 8, 1, 9, tzinfo=UTC)  # before target_time

    matured = join_matured_predictions([prediction], [], now_utc=now)
    metrics = calculate_delayed_metrics(matured, horizon_hours=6)

    assert metrics.n_matured == 0
    assert metrics.n_total == 1
    assert metrics.mae_cm is None
    assert metrics.rmse_cm is None


def test_calculate_delayed_metrics_filters_by_horizon() -> None:
    predictions = [_prediction(6, 10, 98.0, "p1"), _prediction(12, 16, 90.0, "p2")]
    hourly = [_hourly(10, value=100.0), _hourly(16, value=95.0)]
    now = datetime(2024, 8, 1, 17, tzinfo=UTC)

    matured = join_matured_predictions(predictions, hourly, now_utc=now)
    metrics_6h = calculate_delayed_metrics(matured, horizon_hours=6)
    metrics_12h = calculate_delayed_metrics(matured, horizon_hours=12)

    assert metrics_6h.n_total == 1
    assert metrics_12h.n_total == 1
    assert metrics_6h.mae_cm == 2.0
    assert metrics_12h.mae_cm == 5.0
