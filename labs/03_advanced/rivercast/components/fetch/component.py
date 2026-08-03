"""Fetch component: pull raw measurements for one station and archive them
to bronze (PLAN.md Phase 3 adapters + Phase 8 component contract).

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
    with_git_commit,
)
from rivercast.config import RivercastConfig
from rivercast.ingest import ingest_window
from rivercast.sources.base import GaugeSource
from rivercast.sources.fixture import FixtureGaugeSource
from rivercast.sources.pegelonline import PegelOnlineSource
from rivercast.storage import RawArchive

_LOG = component_logger("fetch")


def _build_source(mode: str, config: RivercastConfig, fixture_dir: Path | None) -> GaugeSource:
    if mode == "fixture":
        if fixture_dir is None:
            raise ValueError("fixture_dir is required when mode='fixture'")
        return FixtureGaugeSource(fixture_dir)
    if mode == "live":
        return PegelOnlineSource(config.source)
    raise ValueError(f"unknown mode {mode!r}; expected 'fixture' or 'live'")


def run(
    config_path: Path,
    lab_root: Path,
    station_uuid: str,
    parameter: str,
    start: datetime,
    end: datetime,
    fixture_dir: Path | None = None,
) -> ComponentResult:
    """Fetch one station/parameter window and archive it to bronze.

    Returns the bronze object key that was written (or the pre-existing key,
    if this exact payload was already archived — fetches are idempotent by
    content, rule 9).
    """
    config = load_component_config(config_path)
    store = open_store(config, lab_root)
    archive = RawArchive(store, config.storage.zones)
    source = _build_source(config.mode, config, fixture_dir)

    outcome = ingest_window(source, archive, station_uuid, parameter, start, end)

    if not outcome.parsed_ok:
        _LOG.error(
            "fetch archived a malformed payload",
            extra={"station_uuid": station_uuid, "archived_key": outcome.archived_key},
        )
        return ComponentResult(
            component="fetch",
            status="failed",
            output_keys=[outcome.archived_key],
            metadata={
                "station_uuid": station_uuid,
                "parameter": parameter,
                "error": outcome.error,
                "archive_created": outcome.archive_created,
            },
            code_commit=with_git_commit(lab_root),
        )

    _LOG.info(
        "fetched and archived",
        extra={
            "station_uuid": station_uuid,
            "archived_key": outcome.archived_key,
            "measurement_count": len(outcome.measurements),
        },
    )
    return ComponentResult(
        component="fetch",
        status="ok",
        output_keys=[outcome.archived_key],
        metadata={
            "station_uuid": station_uuid,
            "parameter": parameter,
            "measurement_count": len(outcome.measurements),
            "archive_created": outcome.archive_created,
        },
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fetch and archive one station's measurements")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--station-uuid", required=True)
    parser.add_argument("--parameter", default="W")
    parser.add_argument("--start", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--end", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--fixture-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        station_uuid=args.station_uuid,
        parameter=args.parameter,
        start=datetime.fromisoformat(args.start).astimezone(UTC),
        end=datetime.fromisoformat(args.end).astimezone(UTC),
        fixture_dir=args.fixture_dir,
    )
    emit(result)


if __name__ == "__main__":
    main()
