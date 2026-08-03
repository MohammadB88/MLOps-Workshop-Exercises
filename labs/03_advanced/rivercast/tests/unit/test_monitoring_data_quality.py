"""Tests for the data-monitoring report (PLAN.md Phase 12)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rivercast.contracts.hourly import HourlyObservation
from rivercast.monitoring.data_quality import run_data_quality_report
from rivercast.processing.quality import QualityReport

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"


def _hourly(hour: int, value: float | None, missing: bool = False) -> HourlyObservation:
    return HourlyObservation(
        station_uuid=STATION,
        station_name="KAUB",
        parameter="W",
        hour_utc=datetime(2024, 8, 1, hour, tzinfo=UTC),
        value=value,
        is_missing=missing,
    )


def test_report_summarizes_row_and_station_counts() -> None:
    hourly = [_hourly(h, value=100.0 + h) for h in range(5)]
    quality_report = QualityReport(
        issues=[], checked_at_utc="2024-08-01T00:00:00+00:00", row_count=5
    )

    report = run_data_quality_report(hourly, quality_report)

    assert report.row_count == 5
    assert report.station_count == 1
    assert report.missing_row_count == 0
    assert report.evidently_snapshot_json


def test_report_counts_missing_rows() -> None:
    hourly = [_hourly(h, value=None, missing=True) for h in range(3)] + [
        _hourly(3, value=100.0, missing=False)
    ]
    quality_report = QualityReport(
        issues=[], checked_at_utc="2024-08-01T00:00:00+00:00", row_count=4
    )

    report = run_data_quality_report(hourly, quality_report)

    assert report.missing_row_count == 3


def test_empty_window_fails_closed() -> None:
    quality_report = QualityReport(
        issues=[], checked_at_utc="2024-08-01T00:00:00+00:00", row_count=0
    )
    with pytest.raises(ValueError, match="empty"):
        run_data_quality_report([], quality_report)
