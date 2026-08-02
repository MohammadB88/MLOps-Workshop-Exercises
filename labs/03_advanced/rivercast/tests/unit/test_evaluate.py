"""Evaluation tests: metrics correctness, skill sign, slicing, edge cases."""

import numpy as np
import pandas as pd
import pytest

from rivercast.models.evaluate import (
    evaluate_predictions,
    rising_falling_slices,
    skill_vs_persistence,
    water_level_quantile_slices,
)


def test_skill_positive_when_candidate_beats_persistence() -> None:
    assert skill_vs_persistence(candidate_mae=1.0, persistence_mae=2.0) == pytest.approx(0.5)


def test_skill_negative_when_candidate_worse_than_persistence() -> None:
    assert skill_vs_persistence(candidate_mae=3.0, persistence_mae=2.0) == pytest.approx(-0.5)


def test_skill_zero_when_equal() -> None:
    assert skill_vs_persistence(candidate_mae=2.0, persistence_mae=2.0) == pytest.approx(0.0)


def test_skill_undefined_persistence_mae_zero() -> None:
    with pytest.raises(ValueError, match="undefined"):
        skill_vs_persistence(1.0, 0.0)


def test_evaluate_predictions_perfect_candidate() -> None:
    y_true = pd.Series([10.0, 20.0, 30.0])
    y_pred = np.array([10.0, 20.0, 30.0])
    persistence_pred = np.array([9.0, 21.0, 28.0])
    report = evaluate_predictions("candidate", 6, y_true, y_pred, persistence_pred)
    assert report.mae_cm == 0.0
    assert report.rmse_cm == 0.0
    assert report.skill_vs_persistence == 1.0  # perfect model: skill == 1


def test_evaluate_predictions_matches_persistence_exactly() -> None:
    y_true = pd.Series([10.0, 20.0, 30.0])
    same_pred = np.array([9.0, 21.0, 28.0])
    report = evaluate_predictions("candidate", 6, y_true, same_pred, same_pred)
    assert report.skill_vs_persistence == pytest.approx(0.0)


def test_evaluate_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="equal length"):
        evaluate_predictions("m", 6, pd.Series([1.0, 2.0]), np.array([1.0]), np.array([1.0, 1.0]))


def test_evaluate_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate_predictions("m", 6, pd.Series([], dtype=float), np.array([]), np.array([]))


def test_slices_produce_per_group_metrics() -> None:
    y_true = pd.Series([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([10.0, 21.0, 29.0, 44.0])
    persistence_pred = np.array([9.0, 19.0, 31.0, 39.0])
    season = pd.Series(["summer", "summer", "winter", "winter"])
    report = evaluate_predictions(
        "candidate", 6, y_true, y_pred, persistence_pred, slice_labels={"season": season}
    )
    values = {s.slice_value for s in report.slices}
    assert values == {"summer", "winter"}
    summer_slice = next(s for s in report.slices if s.slice_value == "summer")
    assert summer_slice.n == 2


def test_rising_falling_slices_labels_correctly() -> None:
    level = pd.Series([100.0, 101.0, 102.0], index=[0, 1, 2])
    delta = pd.Series([0.0, 1.0, -1.0], index=[0, 1, 2])
    labels = rising_falling_slices(level, delta)
    assert list(labels) == ["steady", "rising", "falling"]


def test_water_level_quantile_slices_covers_all_rows() -> None:
    level = pd.Series(range(100), dtype=float)
    labels = water_level_quantile_slices(level)
    assert set(labels) <= {"low", "mid", "high"}
    assert len(labels) == 100
    assert (labels == "low").sum() > 0
    assert (labels == "high").sum() > 0
