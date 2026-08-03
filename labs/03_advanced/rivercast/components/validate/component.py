"""Validate component: data-quality gate over a silver hourly window
(PLAN.md Phase 4 quality checks + Phase 8 component contract).

Reads the hourly observations ``components.transform`` wrote to silver, runs
the full quality-check battery, and writes a quality report to
``reports/data_quality/``. Fails closed (rule 13): any ``severity="error"``
issue makes this component's status ``"failed"``, which a caller must treat
as "stop before training" — this component never partially passes.

Container image: ``rivercast-data`` (Containerfile.data).
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    read_json,
    with_git_commit,
    write_json,
)
from rivercast.contracts.hourly import HourlyObservation
from rivercast.processing import QualityIssue, QualityReport
from rivercast.processing.quality import check_short_gap_missingness
from rivercast.storage import zone_key

_LOG = component_logger("validate")


def run(
    config_path: Path,
    lab_root: Path,
    silver_key: str,
    now_utc: datetime | None = None,
) -> ComponentResult:
    """Validate one silver hourly artifact; write a quality report either way."""
    config = load_component_config(config_path)
    store = open_store(config, lab_root)

    raw_rows = read_json(store, silver_key)
    hourly = [HourlyObservation.model_validate(row) for row in raw_rows]
    # run_checks() takes CanonicalObservation-shaped bounds/freshness checks
    # over native-cadence data; at the hourly-gate stage we only have the
    # already-resampled grid, so we check what's meaningful for it: required
    # station coverage and short-gap missingness. Value-bounds and freshness
    # are checked earlier, over CanonicalObservation, inside `transform`'s
    # own normalize step (normalize_measurements never emits out-of-schema
    # records) -- this gate specifically catches gaps and missing stations
    # that only become visible once data is on the canonical hourly grid.
    required_uuids = {s.uuid for s in config.stations if s.uuid is not None}
    present_uuids = {h.station_uuid for h in hourly}
    missing_stations = required_uuids - present_uuids

    issues: list[QualityIssue] = []
    if missing_stations:
        issues.append(
            QualityIssue(
                "station_coverage",
                "error",
                f"no hourly data for station(s): {sorted(missing_stations)}",
            )
        )
    issues += check_short_gap_missingness(
        hourly, config.thresholds.data_quality.max_short_gap_minutes
    )
    report = QualityReport(
        issues=issues,
        checked_at_utc=(now_utc or datetime.now(UTC)).isoformat(timespec="seconds"),
        row_count=len(hourly),
    )

    report_key = zone_key(
        config.storage.zones,
        "reports",
        "data_quality",
        f"{silver_key.rsplit('/', 1)[-1].removesuffix('.json')}_report.json",
    )
    write_json(
        store,
        report_key,
        {
            "checked_at_utc": report.checked_at_utc,
            "row_count": report.row_count,
            "passed": report.passed,
            "issues": [
                {"check": i.check, "severity": i.severity, "message": i.message}
                for i in report.issues
            ],
        },
        overwrite=True,
    )

    if not report.passed:
        _LOG.error(
            "validate failed: error-severity issues present",
            extra={"errors": [i.message for i in report.errors]},
        )
        return ComponentResult(
            component="validate",
            status="failed",
            output_keys=[report_key],
            metadata={"passed": False, "errors": [i.message for i in report.errors]},
            code_commit=with_git_commit(lab_root),
        )

    _LOG.info("validate passed", extra={"row_count": report.row_count})
    return ComponentResult(
        component="validate",
        status="ok",
        output_keys=[report_key],
        metadata={"passed": True, "warning_count": len(report.issues)},
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate a silver hourly window")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--silver-key", required=True)
    args = parser.parse_args(argv)

    result = run(config_path=args.config, lab_root=args.lab_root, silver_key=args.silver_key)
    emit(result)


if __name__ == "__main__":
    main()
