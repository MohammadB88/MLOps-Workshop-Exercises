"""Data-quality check tests: fail-closed behavior, thresholds, aggregation."""

from datetime import UTC, datetime

from rivercast.contracts.hourly import CanonicalObservation, HourlyObservation
from rivercast.processing.quality import (
    check_conflicts,
    check_freshness,
    check_monotonic_per_station,
    check_required_stations,
    check_short_gap_missingness,
    check_value_bounds,
    run_checks,
)

STATION = "1d26e504-7f9e-480a-b52c-5932be6549ab"
OTHER_STATION = "a37a9aa3-45e9-4d90-9df6-109f3a28a5af"


def _obs(hour: int, value: float, station: str = STATION) -> CanonicalObservation:
    return CanonicalObservation(
        station_uuid=station,
        station_name="KAUB",
        water_body="RHEIN",
        parameter="W",
        observed_at_utc=datetime(2024, 8, 1, hour, tzinfo=UTC),
        source_offset="+00:00",
        value=value,
        unit="cm",
        quality_status="ok",
        ingested_at_utc=datetime(2024, 8, 1, 12, tzinfo=UTC),
        source_sha256="a" * 64,
    )


def _hourly(hour: int, missing: bool, value: float | None = 100.0) -> HourlyObservation:
    return HourlyObservation(
        station_uuid=STATION,
        station_name="KAUB",
        parameter="W",
        hour_utc=datetime(2024, 8, 1, hour, tzinfo=UTC),
        value=None if missing else value,
        is_missing=missing,
    )


def test_value_bounds_passes_within_range() -> None:
    assert check_value_bounds([_obs(0, 100.0)], -200, 1500) == []


def test_value_bounds_flags_out_of_range() -> None:
    issues = check_value_bounds([_obs(0, 9999.0)], -200, 1500)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].check == "value_bounds"


def test_monotonic_passes_for_sorted_unique() -> None:
    assert check_monotonic_per_station([_obs(0, 1.0), _obs(1, 2.0)]) == []


def test_monotonic_flags_out_of_order() -> None:
    issues = check_monotonic_per_station([_obs(1, 2.0), _obs(0, 1.0)])
    assert any(i.check == "monotonic_timestamps" for i in issues)


def test_monotonic_flags_duplicate_natural_key() -> None:
    same_obs = _obs(0, 1.0)
    issues = check_monotonic_per_station([same_obs, same_obs])
    assert any("duplicate" in i.message for i in issues)


def test_required_stations_passes_when_all_present() -> None:
    issues = check_required_stations([_obs(0, 1.0, STATION)], {STATION})
    assert issues == []


def test_required_stations_flags_missing() -> None:
    issues = check_required_stations([_obs(0, 1.0, STATION)], {STATION, OTHER_STATION})
    assert len(issues) == 1
    assert OTHER_STATION in issues[0].message


def test_freshness_passes_when_recent() -> None:
    now = datetime(2024, 8, 1, 0, 30, tzinfo=UTC)
    issues = check_freshness([_obs(0, 1.0)], STATION, "W", now, max_staleness_minutes=60)
    assert issues == []


def test_freshness_fails_when_stale() -> None:
    now = datetime(2024, 8, 1, 5, 0, tzinfo=UTC)
    issues = check_freshness([_obs(0, 1.0)], STATION, "W", now, max_staleness_minutes=60)
    assert len(issues) == 1
    assert issues[0].severity == "error"


def test_freshness_fails_when_no_data_at_all() -> None:
    now = datetime(2024, 8, 1, 0, 30, tzinfo=UTC)
    issues = check_freshness([], STATION, "W", now, max_staleness_minutes=60)
    assert len(issues) == 1
    assert "no observations" in issues[0].message


def test_short_gap_within_threshold_is_not_flagged() -> None:
    hourly = [_hourly(0, False), _hourly(1, True), _hourly(2, False)]
    issues = check_short_gap_missingness(hourly, max_short_gap_minutes=180)
    assert issues == []


def test_short_gap_beyond_threshold_is_a_warning_not_error() -> None:
    hourly = [_hourly(h, True) for h in range(5)]  # 5-hour gap = 300 min
    issues = check_short_gap_missingness(hourly, max_short_gap_minutes=180)
    assert len(issues) == 1
    assert issues[0].severity == "warning"


def test_conflicts_zero_produces_no_issue() -> None:
    assert check_conflicts(0) == []


def test_conflicts_nonzero_is_warning() -> None:
    issues = check_conflicts(3)
    assert len(issues) == 1
    assert issues[0].severity == "warning"


def test_run_checks_aggregates_and_passed_reflects_errors_only() -> None:
    now = datetime(2024, 8, 1, 0, 30, tzinfo=UTC)
    report = run_checks(
        [_obs(0, 100.0)],
        required_station_uuids={STATION},
        freshness_check=(STATION, "W", now),
        value_bounds_cm=(-200, 1500),
        conflict_count=1,  # warning only
        now_utc=now,
    )
    assert report.passed  # only a warning present
    assert report.row_count == 1
    assert len(report.errors) == 0


def test_run_checks_fails_closed_on_bounds_violation() -> None:
    report = run_checks([_obs(0, 99999.0)], value_bounds_cm=(-200, 1500))
    assert not report.passed
    assert any(i.check == "value_bounds" for i in report.errors)
