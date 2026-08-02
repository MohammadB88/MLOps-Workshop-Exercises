"""Data-quality checks over canonical and hourly observations (PLAN.md Phase 4).

Every check returns a :class:`QualityIssue` list; ``run_checks`` aggregates
them into a :class:`QualityReport`. Fail-closed (rule 13): callers must treat
any ``severity="error"`` issue as a reason to stop the pipeline before this
data reaches training or forecasting. ``severity="warning"`` issues (e.g.
missingness under the short-gap threshold) do not block by themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from rivercast.contracts.hourly import CanonicalObservation, HourlyObservation

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class QualityIssue:
    check: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class QualityReport:
    issues: list[QualityIssue]
    checked_at_utc: str
    row_count: int

    @property
    def errors(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def passed(self) -> bool:
        return not self.errors


def check_value_bounds(
    observations: list[CanonicalObservation], min_cm: float, max_cm: float
) -> list[QualityIssue]:
    out_of_bounds = [obs for obs in observations if not (min_cm <= obs.value <= max_cm)]
    if not out_of_bounds:
        return []
    sample = out_of_bounds[:5]
    return [
        QualityIssue(
            "value_bounds",
            "error",
            f"{len(out_of_bounds)} observation(s) outside [{min_cm}, {max_cm}] cm, "
            f"e.g. {[(o.station_uuid, o.observed_at_utc.isoformat(), o.value) for o in sample]}",
        )
    ]


def check_monotonic_per_station(observations: list[CanonicalObservation]) -> list[QualityIssue]:
    """Within one station+parameter, observed_at_utc must be strictly increasing
    once duplicates are removed by :func:`~rivercast.processing.normalize.normalize_measurements`.
    """
    by_series: dict[tuple[str, str], list[datetime]] = {}
    for obs in observations:
        by_series.setdefault((obs.station_uuid, obs.parameter), []).append(obs.observed_at_utc)

    issues = []
    for (station_uuid, parameter), timestamps in by_series.items():
        ordered = sorted(timestamps)
        if ordered != timestamps:
            issues.append(
                QualityIssue(
                    "monotonic_timestamps",
                    "error",
                    f"station {station_uuid} parameter {parameter} is not pre-sorted by "
                    "observed_at_utc",
                )
            )
        if len(set(ordered)) != len(ordered):
            issues.append(
                QualityIssue(
                    "monotonic_timestamps",
                    "error",
                    f"station {station_uuid} parameter {parameter} has duplicate "
                    "observed_at_utc after normalization",
                )
            )
    return issues


def check_required_stations(
    observations: list[CanonicalObservation], required_uuids: set[str]
) -> list[QualityIssue]:
    present = {obs.station_uuid for obs in observations}
    missing = required_uuids - present
    if not missing:
        return []
    return [
        QualityIssue(
            "station_coverage",
            "error",
            f"no observations for required station(s): {sorted(missing)}",
        )
    ]


def check_freshness(
    observations: list[CanonicalObservation],
    station_uuid: str,
    parameter: str,
    now_utc: datetime,
    max_staleness_minutes: float,
) -> list[QualityIssue]:
    matching = [
        obs
        for obs in observations
        if obs.station_uuid == station_uuid and obs.parameter == parameter
    ]
    if not matching:
        return [
            QualityIssue(
                "freshness",
                "error",
                f"no observations at all for station {station_uuid}/{parameter}",
            )
        ]
    latest = max(obs.observed_at_utc for obs in matching)
    age_minutes = (now_utc - latest).total_seconds() / 60.0
    if age_minutes > max_staleness_minutes:
        return [
            QualityIssue(
                "freshness",
                "error",
                f"station {station_uuid}/{parameter} latest observation is "
                f"{age_minutes:.1f} min old (limit {max_staleness_minutes})",
            )
        ]
    return []


def check_short_gap_missingness(
    hourly: list[HourlyObservation], max_short_gap_minutes: float
) -> list[QualityIssue]:
    """Warn (do not fail) when a run of consecutive missing hours exceeds the
    short-gap threshold — this flags the gap for review without stopping the
    pipeline; large permanent gaps stay explicit in the data either way.
    """
    ordered = sorted(hourly, key=lambda h: h.hour_utc)
    issues: list[QualityIssue] = []
    run_start: datetime | None = None
    run_len = 0
    for point in [*ordered, None]:
        if point is not None and point.is_missing:
            if run_start is None:
                run_start = point.hour_utc
            run_len += 1
            continue
        if run_start is not None:
            gap_minutes = run_len * 60
            if gap_minutes > max_short_gap_minutes:
                issues.append(
                    QualityIssue(
                        "short_gap_missingness",
                        "warning",
                        f"gap of {run_len} missing hour(s) starting {run_start.isoformat()} "
                        f"exceeds {max_short_gap_minutes} min threshold",
                    )
                )
            run_start, run_len = None, 0
    return issues


def check_conflicts(conflict_count: int) -> list[QualityIssue]:
    if conflict_count == 0:
        return []
    return [
        QualityIssue(
            "conflicts",
            "warning",
            f"{conflict_count} conflicting duplicate observation(s) resolved",
        )
    ]


def run_checks(
    observations: list[CanonicalObservation],
    *,
    hourly: list[HourlyObservation] | None = None,
    required_station_uuids: set[str] | None = None,
    freshness_check: tuple[str, str, datetime] | None = None,
    value_bounds_cm: tuple[float, float] = (-200.0, 1500.0),
    max_staleness_minutes: float = 120.0,
    max_short_gap_minutes: float = 180.0,
    conflict_count: int = 0,
    now_utc: datetime | None = None,
) -> QualityReport:
    """Run the full battery and aggregate into one report (rule 13: fail closed)."""
    now = now_utc or datetime.now(UTC)
    issues: list[QualityIssue] = []
    issues += check_value_bounds(observations, *value_bounds_cm)
    issues += check_monotonic_per_station(observations)
    if required_station_uuids:
        issues += check_required_stations(observations, required_station_uuids)
    if freshness_check is not None:
        station_uuid, parameter, at = freshness_check
        issues += check_freshness(observations, station_uuid, parameter, at, max_staleness_minutes)
    if hourly is not None:
        issues += check_short_gap_missingness(hourly, max_short_gap_minutes)
    issues += check_conflicts(conflict_count)
    return QualityReport(
        issues=issues,
        checked_at_utc=now.isoformat(timespec="seconds"),
        row_count=len(observations),
    )
