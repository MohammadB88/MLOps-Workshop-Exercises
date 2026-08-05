"""Retention-report tests (PLAN.md Phase 15). Report-only: these tests
confirm what would be listed, never that anything gets deleted -- there is
no delete path to test (see ``rivercast.retention`` module docstring)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rivercast.retention import build_retention_report
from rivercast.storage import LocalObjectStore


@pytest.fixture()
def store(tmp_path: Path) -> LocalObjectStore:
    return LocalObjectStore(tmp_path / "artifacts")


def test_bronze_keys_older_than_retention_are_listed(store: LocalObjectStore) -> None:
    old_key = (
        "bronze/source=pegelonline-rest-v2/parameter=W/station_uuid=abc/"
        "event_date=2024-01-01/fetched_at=20240101T000000Z-abcdef123456.json"
    )
    recent_key = (
        "bronze/source=pegelonline-rest-v2/parameter=W/station_uuid=abc/"
        "event_date=2026-08-01/fetched_at=20260801T000000Z-abcdef654321.json"
    )
    store.put_bytes(old_key, b"{}")
    store.put_bytes(recent_key, b"{}")

    report = build_retention_report(
        store,
        "bronze",
        "bronze",
        retention_days=90,
        now=datetime(2026, 8, 4, tzinfo=UTC),
    )
    assert report.total_keys_scanned == 2
    assert [c.key for c in report.candidates] == [old_key]
    assert report.candidates[0].as_of_date == "2024-01-01"


def test_predictions_keys_older_than_retention_are_listed(store: LocalObjectStore) -> None:
    old_key = "predictions/horizon_hours=6/issued_at=20240101T000000Z-pred1.json"
    recent_key = "predictions/horizon_hours=6/issued_at=20260801T000000Z-pred2.json"
    store.put_bytes(old_key, b"{}")
    store.put_bytes(recent_key, b"{}")

    report = build_retention_report(
        store,
        "predictions",
        "predictions",
        retention_days=180,
        now=datetime(2026, 8, 4, tzinfo=UTC),
    )
    assert [c.key for c in report.candidates] == [old_key]


def test_keys_with_no_parseable_date_are_excluded_not_guessed(store: LocalObjectStore) -> None:
    store.put_bytes("bronze/malformed/not-a-partitioned-key.json", b"{}")
    report = build_retention_report(
        store, "bronze", "bronze", retention_days=1, now=datetime(2026, 8, 4, tzinfo=UTC)
    )
    assert report.total_keys_scanned == 1
    assert report.candidates == []


def test_unknown_zone_raises(store: LocalObjectStore) -> None:
    with pytest.raises(ValueError, match="not defined for zone"):
        build_retention_report(store, "silver", "silver", retention_days=1)
