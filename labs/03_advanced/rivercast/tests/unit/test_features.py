"""Feature engineering tests: shape, determinism, missingness, calendar encoding."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from rivercast.contracts.hourly import HourlyObservation
from rivercast.processing.features import build_features

KAUB = "1d26e504-7f9e-480a-b52c-5932be6549ab"
BINGEN = "0309cd61-90c9-470e-99d4-2ee4fb2c5f84"
PREFIXES = {KAUB: "kaub", BINGEN: "bingen"}
START = datetime(2024, 8, 1, 0, tzinfo=UTC)


def _series(station: str, values: list[float | None]) -> list[HourlyObservation]:
    return [
        HourlyObservation(
            station_uuid=station,
            station_name=station[:4],
            parameter="W",
            hour_utc=START + timedelta(hours=i),
            value=v,
            is_missing=v is None,
            source_lag_minutes=None if v is None else 0.0,
        )
        for i, v in enumerate(values)
    ]


def test_build_features_expected_columns_present() -> None:
    values = [100.0 + i for i in range(12)]
    hourly = _series(KAUB, values) + _series(BINGEN, values)
    features = build_features(hourly, KAUB, [BINGEN], PREFIXES)

    expected = {
        "kaub_level_t",
        "kaub_lag_1h",
        "kaub_lag_3h",
        "kaub_lag_6h",
        "kaub_delta_1h",
        "kaub_delta_6h",
        "kaub_roll_mean_6h",
        "kaub_roll_std_6h",
        "missing_kaub",
        "bingen_level_t",
        "bingen_delta_1h",
        "missing_bingen",
        "hour_sin",
        "hour_cos",
        "day_of_year_sin",
        "day_of_year_cos",
    }
    assert expected <= set(features.columns)
    assert len(features) == 12


def test_missing_indicator_reflects_missing_hours() -> None:
    values: list[float | None] = [100.0, None, 102.0]
    hourly = _series(KAUB, values) + _series(BINGEN, [1.0, 2.0, 3.0])
    features = build_features(hourly, KAUB, [BINGEN], PREFIXES)
    assert list(features["missing_kaub"]) == [0, 1, 0]
    assert (
        features.loc[START + timedelta(hours=1), "kaub_level_t"]
        != features.loc[START + timedelta(hours=1), "kaub_level_t"]
    )  # NaN != NaN


def test_calendar_features_bounded_and_periodic() -> None:
    values = [float(i) for i in range(48)]
    hourly = _series(KAUB, values) + _series(BINGEN, values)
    features = build_features(hourly, KAUB, [BINGEN], PREFIXES)
    for col in ("hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos"):
        assert features[col].between(-1.0, 1.0).all()
    # Same hour-of-day, 24h apart -> identical hour_sin/hour_cos.
    t0 = START
    t24 = START + timedelta(hours=24)
    assert features.loc[t0, "hour_sin"] == pytest.approx(features.loc[t24, "hour_sin"])
    assert features.loc[t0, "hour_cos"] == pytest.approx(features.loc[t24, "hour_cos"])


def test_build_features_is_deterministic() -> None:
    values = [100.0 + i for i in range(12)]
    hourly = _series(KAUB, values) + _series(BINGEN, values)
    first = build_features(list(hourly), KAUB, [BINGEN], PREFIXES)
    second = build_features(list(reversed(hourly)), KAUB, [BINGEN], PREFIXES)
    pd.testing.assert_frame_equal(first, second)


def test_missing_column_prefix_raises() -> None:
    values = [100.0] * 5
    hourly = _series(KAUB, values) + _series(BINGEN, values)
    with pytest.raises(ValueError, match="no column prefix"):
        build_features(hourly, KAUB, [BINGEN], {KAUB: "kaub"})


def test_no_data_for_station_raises() -> None:
    with pytest.raises(ValueError, match="no hourly observations"):
        build_features([], KAUB, [], {KAUB: "kaub"})
