"""Normalization tests: dedup, conflict resolution, determinism, unit mapping."""

from datetime import UTC, datetime

import pytest

from rivercast.contracts.raw import Measurement
from rivercast.processing.normalize import normalize_measurements

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"
SHA = "a" * 64
INGESTED = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def _measurement(ts_raw: str, value: float) -> Measurement:
    parsed = datetime.fromisoformat(ts_raw)
    return Measurement(
        station_uuid=STATION,
        parameter="W",
        timestamp_raw=ts_raw,
        timestamp_utc=parsed.astimezone(UTC),
        value=value,
    )


def test_normalize_maps_fields_and_unit() -> None:
    result = normalize_measurements(
        [_measurement("2024-08-01T02:00:00+02:00", 101.0)], "KAUB", "RHEIN", SHA, INGESTED
    )
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.station_uuid == STATION
    assert obs.station_name == "KAUB"
    assert obs.water_body == "RHEIN"
    assert obs.unit == "cm"
    assert obs.source_offset == "+02:00"
    assert obs.observed_at_utc == datetime(2024, 8, 1, 0, 0, tzinfo=UTC)
    assert obs.quality_status == "ok"
    assert obs.source_sha256 == SHA


def test_exact_duplicate_is_deduplicated_without_conflict() -> None:
    result = normalize_measurements(
        [
            _measurement("2024-08-01T02:00:00+02:00", 101.0),
            _measurement("2024-08-01T02:00:00+02:00", 101.0),
        ],
        "KAUB",
        "RHEIN",
        SHA,
        INGESTED,
    )
    assert len(result.observations) == 1
    assert result.conflicts == []


def test_conflicting_values_keep_larger_and_record_conflict() -> None:
    result = normalize_measurements(
        [
            _measurement("2024-08-01T02:00:00+02:00", 101.0),
            _measurement("2024-08-01T02:00:00+02:00", 105.0),
        ],
        "KAUB",
        "RHEIN",
        SHA,
        INGESTED,
    )
    assert len(result.observations) == 1
    assert result.observations[0].value == 105.0
    assert result.observations[0].quality_status == "conflict"
    assert len(result.conflicts) == 1
    assert result.conflicts[0].kept_value == 105.0
    assert result.conflicts[0].discarded_value == 101.0


def test_output_is_sorted_by_observed_at_utc() -> None:
    result = normalize_measurements(
        [
            _measurement("2024-08-01T04:00:00+02:00", 3.0),
            _measurement("2024-08-01T02:00:00+02:00", 1.0),
            _measurement("2024-08-01T03:00:00+02:00", 2.0),
        ],
        "KAUB",
        "RHEIN",
        SHA,
        INGESTED,
    )
    assert [o.value for o in result.observations] == [1.0, 2.0, 3.0]


def test_normalize_is_deterministic() -> None:
    inputs = [
        _measurement("2024-08-01T02:00:00+02:00", 101.0),
        _measurement("2024-08-01T02:15:00+02:00", 102.0),
    ]
    first = normalize_measurements(list(inputs), "KAUB", "RHEIN", SHA, INGESTED)
    second = normalize_measurements(list(inputs), "KAUB", "RHEIN", SHA, INGESTED)
    assert first.observations == second.observations


def test_unknown_parameter_rejected() -> None:
    bad = Measurement(
        station_uuid=STATION,
        parameter="Q",
        timestamp_raw="2024-08-01T02:00:00+02:00",
        timestamp_utc=datetime(2024, 8, 1, 0, 0, tzinfo=UTC),
        value=1.0,
    )
    with pytest.raises(ValueError, match="unknown parameter"):
        normalize_measurements([bad], "KAUB", "RHEIN", SHA, INGESTED)


def test_empty_input_returns_empty_result() -> None:
    result = normalize_measurements([], "KAUB", "RHEIN", SHA, INGESTED)
    assert result.observations == []
    assert result.conflicts == []
