"""Monitor component: data-freshness and coverage summary over a silver
window (PLAN.md Phase 12 data-monitoring subset available now + Phase 8
component contract).

Only the data-monitoring checks that already exist in
``rivercast.processing.quality`` are wired here (source freshness, row
count, missingness, station coverage). Delayed model-quality monitoring
(rolling MAE, prediction drift, Evidently reports) depends on predictions
and matured labels that don't exist until Phase 9 stores them and Phase 12
builds the join — this component intentionally does not stub that out.

Container image: ``rivercast-ops`` (Containerfile.ops).
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
from rivercast.storage import zone_key

_LOG = component_logger("monitor")


def run(
    config_path: Path,
    lab_root: Path,
    silver_key: str,
    now_utc: datetime | None = None,
) -> ComponentResult:
    """Summarize freshness, coverage, and missingness for one silver window."""
    config = load_component_config(config_path)
    store = open_store(config, lab_root)
    now = now_utc or datetime.now(UTC)

    raw_rows = read_json(store, silver_key)
    hourly = [HourlyObservation.model_validate(row) for row in raw_rows]

    required_uuids = {s.uuid for s in config.stations if s.uuid is not None}
    by_station: dict[str, list[HourlyObservation]] = {}
    for obs in hourly:
        by_station.setdefault(obs.station_uuid, []).append(obs)

    station_summaries = {}
    for station_uuid, rows in by_station.items():
        latest_present = max((r.hour_utc for r in rows if not r.is_missing), default=None)
        staleness_minutes = (
            (now - latest_present).total_seconds() / 60.0 if latest_present is not None else None
        )
        station_summaries[station_uuid] = {
            "row_count": len(rows),
            "missing_count": sum(1 for r in rows if r.is_missing),
            "latest_present_hour_utc": latest_present.isoformat() if latest_present else None,
            "staleness_minutes": staleness_minutes,
        }

    missing_stations = sorted(required_uuids - by_station.keys())
    summary = {
        "checked_at_utc": now.isoformat(timespec="seconds"),
        "silver_key": silver_key,
        "row_count": len(hourly),
        "missing_station_count": len(missing_stations),
        "missing_stations": missing_stations,
        "by_station": station_summaries,
    }

    report_key = zone_key(
        config.storage.zones,
        "reports",
        "monitoring",
        f"{silver_key.rsplit('/', 1)[-1].removesuffix('.json')}_monitor.json",
    )
    write_json(store, report_key, summary, overwrite=True)

    _LOG.info(
        "monitor summary written",
        extra={"row_count": summary["row_count"], "missing_station_count": len(missing_stations)},
    )
    return ComponentResult(
        component="monitor",
        status="ok",
        output_keys=[report_key],
        metadata={
            "row_count": summary["row_count"],
            "missing_station_count": len(missing_stations),
        },
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Summarize freshness and coverage for a silver window"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--silver-key", required=True)
    args = parser.parse_args(argv)

    result = run(config_path=args.config, lab_root=args.lab_root, silver_key=args.silver_key)
    emit(result)


if __name__ == "__main__":
    main()
