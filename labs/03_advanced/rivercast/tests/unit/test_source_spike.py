"""Offline tests for the Phase 2 spike module. No network access (rule 3)."""

import json
import sys
from pathlib import Path

import pytest

LAB_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB_ROOT / "scripts"))

import source_spike  # noqa: E402  (path insert must precede the import)

FIXTURES = LAB_ROOT / "data_fixtures" / "pegelonline"


def _rows(*items: tuple[str, float]) -> list[dict]:
    return [{"timestamp": ts, "value": value} for ts, value in items]


def test_parse_timestamp_requires_offset() -> None:
    parsed = source_spike.parse_timestamp("2026-08-02T15:00:00+02:00")
    assert parsed.utcoffset() is not None
    with pytest.raises(ValueError, match="without offset"):
        source_spike.parse_timestamp("2026-08-02T15:00:00")


def test_analyze_series_clean_grid() -> None:
    rows = _rows(
        ("2026-08-02T15:00:00+02:00", 100.0),
        ("2026-08-02T15:15:00+02:00", 101.0),
        ("2026-08-02T15:30:00+02:00", 102.0),
        ("2026-08-02T15:45:00+02:00", 103.0),
    )
    stats = source_spike.analyze_series(rows)
    assert stats.rows == 4
    assert stats.cadence_minutes_mode == 15
    assert stats.gaps_over_tolerance == 0
    assert stats.duplicate_timestamps == 0
    assert stats.value_min == 100.0 and stats.value_max == 103.0
    assert stats.utc_offsets_seen == ["+02:00"]


def test_analyze_series_detects_gap_duplicate_and_conflict() -> None:
    rows = _rows(
        ("2026-08-02T15:00:00+02:00", 100.0),
        ("2026-08-02T15:15:00+02:00", 101.0),
        ("2026-08-02T15:15:00+02:00", 101.0),  # exact duplicate
        ("2026-08-02T16:30:00+02:00", 102.0),  # 75-minute gap
        ("2026-08-02T16:45:00+02:00", 103.0),
        ("2026-08-02T16:45:00+02:00", 999.0),  # conflicting duplicate
    )
    stats = source_spike.analyze_series(rows)
    assert stats.duplicate_timestamps == 2
    assert stats.conflicting_duplicates == 1
    assert stats.gaps_over_tolerance == 1
    assert stats.max_gap_minutes == 75.0


def test_analyze_series_normalizes_mixed_offsets_to_utc() -> None:
    # Fall-back: 02:30+02:00 == 00:30 UTC, 02:30+01:00 == 01:30 UTC — distinct
    # instants, not duplicates, and a continuous 15-min grid in UTC.
    rows = _rows(
        ("2025-10-26T02:30:00+02:00", 100.0),
        ("2025-10-26T02:45:00+02:00", 101.0),
        ("2025-10-26T02:00:00+01:00", 102.0),
        ("2025-10-26T02:15:00+01:00", 103.0),
        ("2025-10-26T02:30:00+01:00", 104.0),
    )
    stats = source_spike.analyze_series(rows)
    assert stats.duplicate_timestamps == 0
    assert stats.gaps_over_tolerance == 0
    assert stats.utc_offsets_seen == ["+01:00", "+02:00"]
    assert stats.first_utc == "2025-10-26T00:30:00+00:00"
    assert stats.last_utc == "2025-10-26T01:30:00+00:00"


def test_overlap_stats_full_coverage() -> None:
    series = {
        "A": _rows(("2026-08-01T00:00:00+02:00", 1.0), ("2026-08-01T00:15:00+02:00", 2.0)),
        "B": _rows(("2026-08-01T00:00:00+02:00", 3.0), ("2026-08-01T00:15:00+02:00", 4.0)),
    }
    result = source_spike.overlap_stats(series)
    assert result["expected_grid_points"] == 2
    assert result["coverage_fraction"] == {"A": 1.0, "B": 1.0}


def test_pearson_perfect_and_inverse() -> None:
    assert source_spike.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert source_spike.pearson([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)


def test_upstream_lead_correlation_sees_shifted_signal() -> None:
    # Upstream is a noiseless copy of the target led by 6 hours: the upstream
    # current delta must correlate perfectly with the target's future delta.
    hours = 48
    target = [
        {
            "timestamp": f"2026-07-{1 + h // 24:02d}T{h % 24:02d}:00:00+02:00",
            "value": float(h * h % 37),
        }
        for h in range(hours)
    ]
    upstream = [
        {"timestamp": t["timestamp"], "value": target[min(h + 6, hours - 1)]["value"]}
        for h, t in enumerate(target)
    ]
    result = source_spike.upstream_lead_correlation(target, upstream, lead_hours=6)
    assert result["n"] > 10
    assert result["corr_upstream_delta_vs_future"] > 0.99


# ---------------------------------------------------------------------------
# Contract tests over the committed fixtures (deterministic, offline)
# ---------------------------------------------------------------------------


def test_fixture_stations_match_pinned_config() -> None:
    import yaml

    stations_yaml = yaml.safe_load((LAB_ROOT / "configs" / "stations.yaml").read_text("utf-8"))
    fixture = json.loads((FIXTURES / "stations_rhein.json").read_text("utf-8"))
    by_name = {s["shortname"]: s for s in fixture}
    for pinned in stations_yaml["stations"]:
        assert pinned["name"] in by_name, f"{pinned['name']} missing from fixture"
        assert by_name[pinned["name"]]["uuid"] == pinned["uuid"]


def test_fixture_recent_series_are_clean_15min_grids() -> None:
    for name in ("MAINZ", "OESTRICH", "BINGEN", "KAUB"):
        rows = json.loads((FIXTURES / "recent" / f"{name}.json").read_text("utf-8"))
        stats = source_spike.analyze_series(rows)
        assert stats.rows > 500, name
        assert stats.cadence_minutes_mode == 15, name
        assert stats.duplicate_timestamps == 0, name


def test_fixture_dst_windows_contain_both_offsets() -> None:
    for label in ("dst_spring_2025", "dst_fall_2025"):
        rows = json.loads((FIXTURES / "historical" / f"{label}_KAUB.json").read_text("utf-8"))
        stats = source_spike.analyze_series(rows)
        assert stats.utc_offsets_seen == ["+01:00", "+02:00"], label
        assert stats.gaps_over_tolerance == 0, label
        assert stats.conflicting_duplicates == 0, label


def test_fixture_earliest_window_starts_january_2000() -> None:
    rows = json.loads((FIXTURES / "historical" / "earliest_2000_KAUB.json").read_text("utf-8"))
    stats = source_spike.analyze_series(rows)
    assert stats.rows > 200
    assert stats.first_utc is not None and stats.first_utc.startswith("2000-01-01")
