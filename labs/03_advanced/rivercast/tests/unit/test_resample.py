"""Hourly resampling tests: tolerance rule, explicit missingness, no interpolation."""

from datetime import UTC, datetime

import pytest

from rivercast.contracts.hourly import CanonicalObservation
from rivercast.processing.resample import hourly_grid, resample_hourly

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"


def _obs(hour: int, minute: int, value: float) -> CanonicalObservation:
    return CanonicalObservation(
        station_uuid=STATION,
        station_name="KAUB",
        water_body="RHEIN",
        parameter="W",
        observed_at_utc=datetime(2024, 8, 1, hour, minute, tzinfo=UTC),
        source_offset="+00:00",
        value=value,
        unit="cm",
        quality_status="ok",
        ingested_at_utc=datetime(2024, 8, 1, 12, 0, tzinfo=UTC),
        source_sha256="a" * 64,
    )


def test_hourly_grid_inclusive() -> None:
    start = datetime(2024, 8, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 8, 1, 3, 0, tzinfo=UTC)
    grid = hourly_grid(start, end)
    assert len(grid) == 4
    assert grid[0] == start and grid[-1] == end


def test_hourly_grid_rejects_non_hour_boundaries() -> None:
    with pytest.raises(ValueError, match="exactly on the hour"):
        hourly_grid(
            datetime(2024, 8, 1, 0, 30, tzinfo=UTC),
            datetime(2024, 8, 1, 3, 0, tzinfo=UTC),
        )


def test_picks_last_reading_at_or_before_hour_within_tolerance() -> None:
    observations = [
        _obs(0, 45, 100.0),
        _obs(1, 50, 101.0),
    ]  # both within 30 min tolerance of hour 1? check
    start = end = datetime(2024, 8, 1, 1, 0, tzinfo=UTC)
    result = resample_hourly(observations, STATION, "KAUB", "W", start, end, tolerance_minutes=30)
    assert len(result) == 1
    # 0:45 is 15 min before hour 1:00 -> within tolerance and <= hour.
    assert result[0].value == 100.0
    assert result[0].is_missing is False
    assert result[0].source_lag_minutes == 15.0


def test_reading_after_hour_is_not_used() -> None:
    observations = [_obs(1, 5, 999.0)]  # 5 min after the hour
    start = end = datetime(2024, 8, 1, 1, 0, tzinfo=UTC)
    result = resample_hourly(observations, STATION, "KAUB", "W", start, end, tolerance_minutes=30)
    assert result[0].is_missing is True
    assert result[0].value is None


def test_gap_beyond_tolerance_is_explicit_missing_not_interpolated() -> None:
    observations = [_obs(0, 0, 100.0), _obs(4, 0, 140.0)]  # 4-hour gap
    start = datetime(2024, 8, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 8, 1, 4, 0, tzinfo=UTC)
    result = resample_hourly(observations, STATION, "KAUB", "W", start, end, tolerance_minutes=30)
    by_hour = {r.hour_utc.hour: r for r in result}
    assert by_hour[0].is_missing is False and by_hour[0].value == 100.0
    assert by_hour[1].is_missing is True
    assert by_hour[2].is_missing is True
    assert by_hour[3].is_missing is True
    assert by_hour[4].is_missing is False and by_hour[4].value == 140.0


def test_within_tolerance_carries_forward_exact_boundary() -> None:
    observations = [_obs(0, 30, 100.0)]  # exactly 30 min before hour 1
    start = end = datetime(2024, 8, 1, 1, 0, tzinfo=UTC)
    result = resample_hourly(observations, STATION, "KAUB", "W", start, end, tolerance_minutes=30)
    assert result[0].is_missing is False
    assert result[0].source_lag_minutes == 30.0


def test_filters_by_station_and_parameter() -> None:
    other_station_obs = CanonicalObservation(
        station_uuid="00000000-0000-0000-0000-000000000000",
        station_name="OTHER",
        water_body="RHEIN",
        parameter="W",
        observed_at_utc=datetime(2024, 8, 1, 0, 0, tzinfo=UTC),
        source_offset="+00:00",
        value=999.0,
        unit="cm",
        quality_status="ok",
        ingested_at_utc=datetime(2024, 8, 1, 12, 0, tzinfo=UTC),
        source_sha256="a" * 64,
    )
    start = end = datetime(2024, 8, 1, 0, 0, tzinfo=UTC)
    result = resample_hourly(
        [other_station_obs], STATION, "KAUB", "W", start, end, tolerance_minutes=30
    )
    assert result[0].is_missing is True  # other station's reading must not leak in


def test_resample_is_deterministic() -> None:
    observations = [_obs(0, 0, 100.0), _obs(1, 0, 101.0), _obs(2, 0, 102.0)]
    start = datetime(2024, 8, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 8, 1, 2, 0, tzinfo=UTC)
    first = resample_hourly(list(observations), STATION, "KAUB", "W", start, end, 30)
    second = resample_hourly(list(reversed(observations)), STATION, "KAUB", "W", start, end, 30)
    assert first == second
