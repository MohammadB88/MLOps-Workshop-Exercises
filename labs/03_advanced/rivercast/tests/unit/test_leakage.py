"""Mandatory leakage tests (PLAN.md Phase 5).

These are not general-purpose feature tests (see test_features.py /
test_labels.py) — each test here maps directly to one leakage rule from the
plan and must keep failing loudly if that rule is ever violated:

1. Mutating observations after `t` must not change the feature row at `t`.
2. Labels must not appear in feature columns.
3. Rolling windows must end at `t` (no centered/forward window).
4. (Fit-only-on-training-window is exercised in Phase 6's split, not here —
   feature generation itself has no fit step to leak through.)
"""

from datetime import UTC, datetime, timedelta

import pandas as pd

from rivercast.contracts.hourly import HourlyObservation
from rivercast.processing.dataset import assemble_dataset
from rivercast.processing.features import build_features
from rivercast.processing.labels import build_labels

KAUB = "1d26e504-7f9e-480a-b52c-5932be6549ab"
BINGEN = "0309cd61-90c9-470e-99d4-2ee4fb2c5f84"
PREFIXES = {KAUB: "kaub", BINGEN: "bingen"}
START = datetime(2024, 8, 1, 0, tzinfo=UTC)


def _series(station: str, start: datetime, values: list[float]) -> list[HourlyObservation]:
    return [
        HourlyObservation(
            station_uuid=station,
            station_name=station[:4],
            parameter="W",
            hour_utc=start + timedelta(hours=i),
            value=v,
            is_missing=False,
            source_lag_minutes=0.0,
        )
        for i, v in enumerate(values)
    ]


def _build(hourly: list[HourlyObservation]) -> pd.DataFrame:
    return build_features(hourly, KAUB, [BINGEN], PREFIXES)


def test_mutating_future_observations_does_not_change_past_feature_row() -> None:
    """Rule 1: changing t+1..t+N must not change the feature row computed at t."""
    baseline_values = [100.0 + i for i in range(24)]
    baseline = _series(KAUB, START, baseline_values) + _series(BINGEN, START, baseline_values)
    features_before = _build(baseline)

    issue_t = START + timedelta(hours=10)
    row_before = features_before.loc[issue_t].copy()

    # Mutate every observation strictly after t (hours 11..23) to wildly
    # different values.
    mutated_values = list(baseline_values)
    for i in range(11, 24):
        mutated_values[i] = -9999.0
    mutated = _series(KAUB, START, mutated_values) + _series(BINGEN, START, mutated_values)
    features_after = _build(mutated)
    row_after = features_after.loc[issue_t]

    pd.testing.assert_series_equal(row_before, row_after, check_names=False)


def test_mutating_the_issue_hour_itself_or_past_does_change_the_row() -> None:
    """Sanity check that the test above is meaningful: past mutations DO propagate."""
    baseline_values = [100.0 + i for i in range(24)]
    baseline = _series(KAUB, START, baseline_values) + _series(BINGEN, START, baseline_values)
    features_before = _build(baseline)

    issue_t = START + timedelta(hours=10)
    mutated_values = list(baseline_values)
    mutated_values[10] = -9999.0  # the issue hour itself
    mutated = _series(KAUB, START, mutated_values) + _series(BINGEN, START, mutated_values)
    features_after = _build(mutated)

    assert (
        features_before.loc[issue_t, "kaub_level_t"] != features_after.loc[issue_t, "kaub_level_t"]
    )


def test_labels_never_appear_among_feature_columns() -> None:
    """Rule 2: label columns must not be present in (or derivable-by-name from) features."""
    values = [100.0 + i for i in range(24)]
    hourly = _series(KAUB, START, values) + _series(BINGEN, START, values)
    features = _build(hourly)
    labels = build_labels(hourly, KAUB, features.index, [6, 12], match_tolerance_minutes=30)

    assert set(labels.columns).isdisjoint(features.columns)
    dataset = assemble_dataset(features, labels)
    # The joined dataset legitimately contains both, but every label column
    # is exactly one of the requested target_level_* columns -- nothing named
    # "target" leaked into what build_features() itself produced.
    assert "target_level_6h" not in features.columns
    assert "target_level_12h" not in features.columns
    for col in features.columns:
        assert not col.startswith("target_level"), col
    assert set(dataset.columns) == set(features.columns) | set(labels.columns)


def test_rolling_window_ends_at_t_not_centered() -> None:
    """Rule 3: roll_mean_6h at t must equal the plain mean of [t-5..t], never
    including t+1 or later (which a centered window would).
    """
    # A monotonic ramp makes centered vs backward windows produce different
    # means, so this test would fail if the window were centered.
    values = [float(i) for i in range(24)]
    hourly = _series(KAUB, START, values) + _series(BINGEN, START, values)
    features = _build(hourly)

    issue_t = START + timedelta(hours=10)
    expected_backward_mean = sum(range(5, 11)) / 6  # values at hours 5..10
    assert features.loc[issue_t, "kaub_roll_mean_6h"] == expected_backward_mean

    # A centered window (hours 7..12, i.e. peeking 2h into the future) would
    # give a different (larger, since the series is increasing) mean.
    centered_mean_if_leaky = sum(range(7, 13)) / 6
    assert features.loc[issue_t, "kaub_roll_mean_6h"] != centered_mean_if_leaky


def test_lag_features_only_reference_past_hours() -> None:
    values = [float(i) for i in range(24)]
    hourly = _series(KAUB, START, values) + _series(BINGEN, START, values)
    features = _build(hourly)

    issue_t = START + timedelta(hours=10)
    row = features.loc[issue_t]
    assert row["kaub_lag_1h"] == 9.0
    assert row["kaub_lag_3h"] == 7.0
    assert row["kaub_lag_6h"] == 4.0
    # None of the lag values can equal or exceed the issue-hour's own value
    # for a strictly increasing series -- if they did, that would mean a lag
    # column picked up a future (or same-hour) reading.
    assert row["kaub_lag_1h"] < row["kaub_level_t"]
    assert row["kaub_lag_3h"] < row["kaub_level_t"]
    assert row["kaub_lag_6h"] < row["kaub_level_t"]


def test_upstream_station_features_do_not_use_future_upstream_readings() -> None:
    """An upstream station's current-hour feature at issue time t must come
    from upstream's own hour <= t, not a later upstream reading.
    """
    kaub_values = [100.0] * 24
    bingen_values = [float(i) for i in range(24)]  # distinguishable ramp
    hourly = _series(KAUB, START, kaub_values) + _series(BINGEN, START, bingen_values)
    features = _build(hourly)

    issue_t = START + timedelta(hours=10)
    assert features.loc[issue_t, "bingen_level_t"] == 10.0  # not 11, 12, ... (future)
