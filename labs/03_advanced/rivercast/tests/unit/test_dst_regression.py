"""DST regression tests over the real 2025 transition fixtures from Phase 2.

Spring-forward (02:00 -> 03:00 CET->CEST) and fall-back (03:00 -> 02:00
CEST->CET) must resample to a clean, gap-free, non-duplicated hourly UTC grid
— the whole point of storing timestamps internally in UTC (rule 6) while
preserving the original offset (rule 7).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from rivercast.contracts.raw import Measurement
from rivercast.processing.normalize import normalize_measurements
from rivercast.processing.resample import resample_hourly

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"
SHA = "a" * 64


def _load_measurements(path: Path) -> list[Measurement]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        Measurement(
            station_uuid=STATION,
            parameter="W",
            timestamp_raw=row["timestamp"],
            timestamp_utc=datetime.fromisoformat(row["timestamp"]).astimezone(UTC),
            value=float(row["value"]),
        )
        for row in rows
    ]


def _resample_fixture(lab_root: Path, filename: str, start: datetime, end: datetime):
    path = lab_root / "data_fixtures" / "pegelonline" / "historical" / filename
    measurements = _load_measurements(path)
    normalized = normalize_measurements(
        measurements, "KAUB", "RHEIN", SHA, datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
    )
    assert normalized.conflicts == []
    return resample_hourly(
        normalized.observations, STATION, "KAUB", "W", start, end, tolerance_minutes=30
    )


def test_spring_forward_2025_produces_gap_free_hourly_grid(lab_root: Path) -> None:
    # CET->CEST transition: 2025-03-30 02:00 local time does not exist.
    start = datetime(2025, 3, 29, 12, 0, tzinfo=UTC)
    end = datetime(2025, 3, 30, 12, 0, tzinfo=UTC)
    hourly = _resample_fixture(lab_root, "dst_spring_2025_KAUB.json", start, end)

    hours = [h.hour_utc for h in hourly]
    assert hours == sorted(set(hours))  # strictly increasing, no duplicates
    assert all((b - a).total_seconds() == 3600 for a, b in zip(hours, hours[1:], strict=False))
    missing = [h for h in hourly if h.is_missing]
    assert missing == [], f"unexpected gaps at {[m.hour_utc for m in missing]}"


def test_fall_back_2025_produces_gap_free_hourly_grid(lab_root: Path) -> None:
    # CEST->CET transition: 2025-10-26 02:00-03:00 local time occurs twice.
    start = datetime(2025, 10, 25, 12, 0, tzinfo=UTC)
    end = datetime(2025, 10, 26, 12, 0, tzinfo=UTC)
    hourly = _resample_fixture(lab_root, "dst_fall_2025_KAUB.json", start, end)

    hours = [h.hour_utc for h in hourly]
    assert hours == sorted(set(hours))  # the repeated local hour must not create a UTC duplicate
    assert all((b - a).total_seconds() == 3600 for a, b in zip(hours, hours[1:], strict=False))
    missing = [h for h in hourly if h.is_missing]
    assert missing == [], f"unexpected gaps at {[m.hour_utc for m in missing]}"


def test_fall_back_repeated_local_hour_normalizes_to_two_distinct_utc_instants(
    lab_root: Path,
) -> None:
    path = lab_root / "data_fixtures" / "pegelonline" / "historical" / "dst_fall_2025_KAUB.json"
    measurements = _load_measurements(path)
    normalized = normalize_measurements(
        measurements, "KAUB", "RHEIN", SHA, datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
    )
    # No conflicts: the two local 02:xx readings (CEST then CET) are genuinely
    # distinct UTC instants, not the same natural key.
    assert normalized.conflicts == []
    utc_timestamps = [obs.observed_at_utc for obs in normalized.observations]
    assert len(utc_timestamps) == len(set(utc_timestamps))
