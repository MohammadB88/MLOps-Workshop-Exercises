"""Tests for feature drift reporting (PLAN.md Phase 12 acceptance criteria)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rivercast.monitoring.drift import run_drift_report


def _stable_frames(n: int = 200, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    reference = pd.DataFrame({"a": rng.normal(100, 5, n), "b": rng.normal(0, 1, n)})
    current = pd.DataFrame({"a": rng.normal(100, 5, n), "b": rng.normal(0, 1, n)})
    return reference, current


def _shifted_frames(n: int = 200, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    reference = pd.DataFrame({"a": rng.normal(100, 5, n), "b": rng.normal(0, 1, n)})
    # Both columns shifted well outside the reference distribution.
    current = pd.DataFrame({"a": rng.normal(160, 5, n), "b": rng.normal(20, 1, n)})
    return reference, current


def test_synthetic_drift_fixture_creates_a_warning() -> None:
    """Plan acceptance: "A synthetic drift fixture creates a warning."""
    reference, current = _shifted_frames()

    report = run_drift_report(reference, current, ["a", "b"], warning_threshold=0.5)

    assert report.drifted_share > 0.5
    assert report.is_warning is True


def test_stable_data_does_not_warn() -> None:
    reference, current = _stable_frames()

    report = run_drift_report(reference, current, ["a", "b"], warning_threshold=0.5)

    assert report.is_warning is False


def test_empty_reference_fails_closed() -> None:
    _, current = _stable_frames()
    with pytest.raises(ValueError, match="reference"):
        run_drift_report(
            pd.DataFrame(columns=["a", "b"]), current, ["a", "b"], warning_threshold=0.5
        )


def test_empty_current_fails_closed() -> None:
    reference, _ = _stable_frames()
    with pytest.raises(ValueError, match="current"):
        run_drift_report(
            reference, pd.DataFrame(columns=["a", "b"]), ["a", "b"], warning_threshold=0.5
        )


def test_missing_column_fails_closed() -> None:
    reference, current = _stable_frames()
    with pytest.raises(ValueError, match="missing"):
        run_drift_report(reference, current, ["a", "does_not_exist"], warning_threshold=0.5)
