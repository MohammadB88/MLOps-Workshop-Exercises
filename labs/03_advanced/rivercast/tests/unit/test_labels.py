"""Label construction tests."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from rivercast.contracts.hourly import HourlyObservation
from rivercast.processing.dataset import assemble_dataset, training_rows
from rivercast.processing.labels import build_labels

KAUB = "1d26e504-7f9e-480a-b52c-5932be6549ab"
START = datetime(2024, 8, 1, 0, tzinfo=UTC)


def _series(values: list[float | None]) -> list[HourlyObservation]:
    return [
        HourlyObservation(
            station_uuid=KAUB,
            station_name="KAUB",
            parameter="W",
            hour_utc=START + timedelta(hours=i),
            value=v,
            is_missing=v is None,
        )
        for i, v in enumerate(values)
    ]


def test_label_matches_future_value_at_exact_horizon() -> None:
    values = [float(i) for i in range(20)]
    hourly = _series(values)
    issue_times = pd.DatetimeIndex([START + timedelta(hours=i) for i in range(10)])
    labels = build_labels(hourly, KAUB, issue_times, [6, 12], match_tolerance_minutes=30)

    assert labels.loc[START, "target_level_6h"] == 6.0
    assert labels.loc[START, "target_level_12h"] == 12.0
    assert labels.loc[START + timedelta(hours=3), "target_level_6h"] == 9.0


def test_label_is_nan_when_future_hour_beyond_available_data() -> None:
    values = [float(i) for i in range(8)]  # only hours 0..7 exist
    hourly = _series(values)
    issue_times = pd.DatetimeIndex([START + timedelta(hours=5)])  # +6h = hour 11, missing
    labels = build_labels(hourly, KAUB, issue_times, [6], match_tolerance_minutes=30)
    assert labels.loc[START + timedelta(hours=5), "target_level_6h"] is None


def test_label_is_nan_when_target_hour_itself_is_missing() -> None:
    values: list[float | None] = [float(i) for i in range(10)]
    values[6] = None  # the hour that would be the +6h label for issue hour 0
    hourly = _series(values)
    issue_times = pd.DatetimeIndex([START])
    labels = build_labels(hourly, KAUB, issue_times, [6], match_tolerance_minutes=30)
    assert pd.isna(labels.loc[START, "target_level_6h"])


def test_negative_tolerance_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        build_labels(_series([1.0]), KAUB, pd.DatetimeIndex([START]), [6], -1)


def test_training_rows_excludes_missing_labels_but_keeps_them_for_forecasting() -> None:
    values = [float(i) for i in range(10)]
    hourly = _series(values)
    issue_times = pd.DatetimeIndex([START + timedelta(hours=i) for i in range(10)])
    labels = build_labels(hourly, KAUB, issue_times, [6], match_tolerance_minutes=30)
    features = pd.DataFrame({"dummy": [0] * len(issue_times)}, index=issue_times)
    dataset = assemble_dataset(features, labels)

    assert len(dataset) == 10  # nothing dropped at assembly time
    trainable = training_rows(dataset, ["target_level_6h"])
    assert len(trainable) == 4  # only issue hours 0..3 have a +6h label within range
    assert trainable["target_level_6h"].notna().all()
