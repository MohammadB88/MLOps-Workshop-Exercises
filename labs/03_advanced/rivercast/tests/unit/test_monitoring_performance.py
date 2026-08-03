"""Tests for delayed performance monitoring and the retraining-decision
artifact (PLAN.md Phase 12 acceptance criteria).
"""

from __future__ import annotations

from datetime import UTC, datetime

from rivercast.contracts.predictions import MaturedPrediction, PredictionRecord
from rivercast.monitoring.performance import evaluate_retraining_signal, rolling_performance_report

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"


def _matured(error_cm: float, prediction_id: str, horizon_hours: int = 6) -> MaturedPrediction:
    prediction = PredictionRecord(
        prediction_id=prediction_id,
        issued_at_utc=datetime(2024, 8, 1, tzinfo=UTC).isoformat(),
        target_time_utc=datetime(2024, 8, 1, 6, tzinfo=UTC).isoformat(),
        horizon_hours=horizon_hours,
        target_station_uuid=STATION,
        prediction_cm=100.0,
        model_name="rivercast-kaub-6h",
        model_version="1",
        model_alias="champion",
        dataset_id="sha256:abc",
        feature_version=1,
    )
    return MaturedPrediction(
        prediction=prediction,
        actual_cm=100.0 + error_cm,
        error_cm=error_cm,
        matured_at_utc=datetime(2024, 8, 1, 6, tzinfo=UTC).isoformat(),
    )


def test_rolling_performance_report_with_no_matured_predictions() -> None:
    """Plan acceptance: "Reports work with no labels" -- an empty matured
    list must still produce a well-formed report, not raise.
    """
    report = rolling_performance_report([], horizon_hours=6, window_label="7d")

    assert report.overall.n_matured == 0
    assert report.overall.mae_cm is None
    assert report.evidently_snapshot_json is None


def test_rolling_performance_report_with_delayed_labels() -> None:
    """Plan acceptance: "Reports work with ... delayed labels" -- once
    predictions mature, the report reflects real accuracy.
    """
    matured = [_matured(0.5, "p1"), _matured(-0.5, "p2"), _matured(1.0, "p3")]

    report = rolling_performance_report(matured, horizon_hours=6, window_label="7d")

    assert report.overall.n_matured == 3
    assert report.overall.mae_cm is not None
    assert report.evidently_snapshot_json is not None


def test_good_performance_does_not_request_retraining() -> None:
    matured = [_matured(0.3, f"p{i}") for i in range(30)]
    report = rolling_performance_report(matured, horizon_hours=6, window_label="all")

    signal = evaluate_retraining_signal(
        report,
        persistence_mae_cm=3.0,
        reference_model_version="1",
        new_labeled_rows=30,
        performance_degradation_mae_ratio=1.2,
        min_matured_predictions_for_signal=24,
    )

    assert signal.requested is False
    assert signal.reasons == []


def test_performance_degradation_requests_retraining() -> None:
    """Plan acceptance: "A performance-degradation fixture creates a
    retraining request."
    """
    matured = [_matured(10.0, f"p{i}") for i in range(30)]
    report = rolling_performance_report(matured, horizon_hours=6, window_label="all")

    signal = evaluate_retraining_signal(
        report,
        persistence_mae_cm=3.0,
        reference_model_version="7",
        new_labeled_rows=30,
        performance_degradation_mae_ratio=1.2,
        min_matured_predictions_for_signal=24,
    )

    assert signal.requested is True
    assert any("rolling_mae_degraded" in reason for reason in signal.reasons)
    assert signal.reference_model_version == "7"
    assert signal.new_labeled_rows == 30


def test_too_few_matured_predictions_withholds_signal_even_if_degraded() -> None:
    """A noisy small-sample MAE must not trigger retraining, even when the
    ratio alone would otherwise trip -- rule 13 in spirit: don't act on
    data too thin to trust.
    """
    matured = [_matured(10.0, f"p{i}") for i in range(5)]
    report = rolling_performance_report(matured, horizon_hours=6, window_label="all")

    signal = evaluate_retraining_signal(
        report,
        persistence_mae_cm=3.0,
        reference_model_version="1",
        new_labeled_rows=5,
        performance_degradation_mae_ratio=1.2,
        min_matured_predictions_for_signal=24,
    )

    assert signal.requested is False


def test_slices_report_rising_falling_and_level_quantile_when_provided() -> None:
    import pandas as pd

    matured = [_matured(0.5 if i % 2 == 0 else -0.5, f"p{i}") for i in range(10)]
    level_now = pd.Series([100.0 + i for i in range(10)])
    delta_1h = pd.Series([1.0 if i % 2 == 0 else -1.0 for i in range(10)])

    report = rolling_performance_report(
        matured, horizon_hours=6, window_label="all", level_now=level_now, delta_1h=delta_1h
    )

    slice_names = {s.slice_name for s in report.slices}
    assert "rising_falling" in slice_names
    assert "level_quantile" in slice_names
