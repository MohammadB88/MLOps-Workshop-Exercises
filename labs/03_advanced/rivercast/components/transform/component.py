"""Transform component: bronze raw fetches -> silver hourly grid -> gold
training dataset (PLAN.md Phases 4-5 processing + Phase 8 component contract).

Reads every bronze object for the configured stations inside
``[start, end)``, normalizes and resamples them to the hourly grid (written
to silver so ``components.validate`` can gate on it independently), then
builds leakage-safe features and labels and writes the assembled dataset
(Parquet) plus its lineage manifest (JSON) to gold. This one component folds
together what the plan's finer-grained Phase 8 list calls "normalize",
"feature generation", and "join labels" — they share one input (bronze) and
gain nothing from being split into separate container steps at this lab's
scale (plan §Phase 8: "do not build one image for every five-line function
unless isolation is necessary").

Container image: ``rivercast-data`` (Containerfile.data).
"""

from __future__ import annotations

import argparse
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    with_git_commit,
    write_json,
)
from rivercast.config import RivercastConfig
from rivercast.contracts.raw import RawFetch, RawFetchMetadata
from rivercast.processing import (
    assemble_dataset,
    build_features,
    build_labels,
    build_manifest,
    normalize_measurements,
    resample_hourly,
)
from rivercast.sources.base import parse_measurements
from rivercast.storage import ObjectStore, zone_key

_LOG = component_logger("transform")


def _bronze_fetches_for_station(
    store: ObjectStore, config: RivercastConfig, station_uuid: str, start: datetime, end: datetime
) -> list[RawFetch]:
    """Every archived raw fetch for one station whose requested window
    overlaps ``[start, end)``, oldest first.
    """
    prefix = zone_key(
        config.storage.zones,
        "bronze",
        f"source={config.source.name if config.mode == 'live' else 'fixture'}",
        f"parameter={config.source.parameter}",
        f"station_uuid={station_uuid}",
    )
    fetches: list[RawFetch] = []
    for key in store.list_keys(f"{prefix}/"):
        if key.endswith(".meta.json") or not key.endswith(".json"):
            continue
        meta_key = f"{key.removesuffix('.json')}.meta.json"
        metadata = RawFetchMetadata.model_validate_json(store.get_bytes(meta_key))
        requested_start = datetime.fromisoformat(metadata.requested_start)
        requested_end = datetime.fromisoformat(metadata.requested_end)
        if requested_end <= start or requested_start >= end:
            continue  # no overlap with the requested window
        fetches.append(RawFetch(payload=store.get_bytes(key), metadata=metadata))
    fetches.sort(key=lambda f: f.metadata.fetched_at_utc)
    return fetches


def _require_uuid(name: str, uuid: str | None) -> str:
    if uuid is None:
        raise ValueError(f"station {name!r} has no resolved UUID; run the Phase 2 spike first")
    return uuid


def run(
    config_path: Path,
    lab_root: Path,
    start: datetime,
    end: datetime,
) -> ComponentResult:
    """Build one gold training dataset from everything archived in bronze
    for ``[start, end)``. Fails closed: any station with zero archived
    fetches in the window stops the run (rule 13) rather than silently
    producing a dataset missing a required input.
    """
    config = load_component_config(config_path)
    store = open_store(config, lab_root)

    target = config.station(config.target_station)
    target_uuid = _require_uuid(target.name, target.uuid)
    upstream = [s for s in config.stations if s.name != config.target_station]
    upstream_uuids = [_require_uuid(s.name, s.uuid) for s in upstream]
    prefixes = {_require_uuid(s.name, s.uuid): s.name.lower() for s in config.stations}

    hourly = []
    checksums: set[str] = set()
    for station in config.stations:
        station_uuid = _require_uuid(station.name, station.uuid)
        fetches = _bronze_fetches_for_station(store, config, station_uuid, start, end)
        if not fetches:
            message = (
                f"no bronze data for station {station.name} ({station_uuid}) in [{start}, {end})"
            )
            _LOG.error(
                "transform stopped: missing station coverage", extra={"station": station.name}
            )
            return ComponentResult(
                component="transform",
                status="failed",
                metadata={"error": message},
                code_commit=with_git_commit(lab_root),
            )

        for fetch in fetches:
            checksums.add(fetch.metadata.sha256)
            normalized = normalize_measurements(
                parse_measurements(fetch),
                station.name,
                station.water_body,
                fetch.metadata.sha256,
                datetime.fromisoformat(fetch.metadata.fetched_at_utc),
            )
            hourly += resample_hourly(
                normalized.observations,
                station_uuid,
                station.name,
                config.source.parameter,
                start,
                end - timedelta(hours=1),
                tolerance_minutes=config.thresholds.data_quality.resample_tolerance_minutes,
            )

    window_tag = f"{start.strftime('%Y%m%dT%H%M%SZ')}_{end.strftime('%Y%m%dT%H%M%SZ')}"
    silver_key = zone_key(config.storage.zones, "silver", "hourly", f"window={window_tag}.json")
    write_json(store, silver_key, [obs.model_dump() for obs in hourly], overwrite=True)

    features = build_features(hourly, target_uuid, upstream_uuids, prefixes)
    labels = build_labels(
        hourly,
        target_uuid,
        pd.DatetimeIndex(features.index),
        config.horizons_hours,
        config.thresholds.labels.match_tolerance_minutes,
    )
    dataset = assemble_dataset(features, labels)
    manifest = build_manifest(
        dataset,
        target_station_uuid=target_uuid,
        input_station_uuids=upstream_uuids,
        horizons_hours=config.horizons_hours,
        source_start_utc=start,
        source_end_utc=end,
        source_checksums=sorted(checksums),
    )

    dataset_prefix = zone_key(
        config.storage.zones, "gold", f"training/dataset_id={manifest.short_id}"
    )
    dataset_key = f"{dataset_prefix}/dataset.parquet"
    manifest_key = f"{dataset_prefix}/manifest.json"

    buffer = io.BytesIO()
    dataset.reset_index().to_parquet(buffer, index=False)
    store.put_bytes(dataset_key, buffer.getvalue(), overwrite=True)
    write_json(store, manifest_key, manifest.model_dump(), overwrite=True)

    _LOG.info(
        "transform wrote gold dataset",
        extra={"dataset_id": manifest.dataset_id, "row_count": manifest.row_count},
    )
    return ComponentResult(
        component="transform",
        status="ok",
        output_keys=[silver_key, dataset_key, manifest_key],
        metadata={"dataset_id": manifest.dataset_id, "row_count": manifest.row_count},
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build a gold training dataset from bronze raw fetches"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--start", required=True, help="ISO-8601 UTC timestamp")
    parser.add_argument("--end", required=True, help="ISO-8601 UTC timestamp")
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        start=datetime.fromisoformat(args.start).astimezone(UTC),
        end=datetime.fromisoformat(args.end).astimezone(UTC),
    )
    emit(result)


if __name__ == "__main__":
    main()
