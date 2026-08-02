"""Immutable bronze archive for raw source responses (PLAN.md Phase 3).

Layout (one object per fetch, plus a metadata sidecar):

    bronze/source=<source>/parameter=<P>/station_uuid=<uuid>/
        event_date=YYYY-MM-DD/fetched_at=<UTC-compact>-<sha256-12>.json
        event_date=YYYY-MM-DD/fetched_at=<UTC-compact>-<sha256-12>.meta.json

``event_date`` is the UTC date of the requested window start; callers that
want day-accurate partitioning fetch day-sized windows (the hourly pipeline
naturally does). Raw objects are never overwritten (rule 9). Writes are
idempotent by content: an identical payload already present in the partition
is detected via the checksum embedded in the object name and skipped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from rivercast.config import StorageZones
from rivercast.contracts.raw import RawFetch
from rivercast.log import get_logger
from rivercast.storage.object_store import ObjectStore
from rivercast.storage.paths import zone_key

_LOG = get_logger("storage.raw_archive")

_CHECKSUM_CHARS = 12


@dataclass(frozen=True)
class ArchiveResult:
    key: str
    metadata_key: str
    created: bool  # False when an identical payload was already archived


def _compact_utc(iso_timestamp: str) -> str:
    """``2026-08-02T17:30:00+00:00`` → ``20260802T173000Z`` (safe for object keys)."""
    parsed = datetime.fromisoformat(iso_timestamp)
    if parsed.tzinfo is None:
        raise ValueError(f"fetched_at_utc must carry an offset: {iso_timestamp!r}")
    return parsed.strftime("%Y%m%dT%H%M%SZ")


class RawArchive:
    def __init__(self, store: ObjectStore, zones: StorageZones) -> None:
        self._store = store
        self._zones = zones

    def _partition(self, fetch: RawFetch) -> str:
        meta = fetch.metadata
        event_date = datetime.fromisoformat(meta.requested_start).date().isoformat()
        return zone_key(
            self._zones,
            "bronze",
            f"source={meta.source}",
            f"parameter={meta.parameter}",
            f"station_uuid={meta.station_uuid}",
            f"event_date={event_date}",
        )

    def store(self, fetch: RawFetch) -> ArchiveResult:
        """Archive one raw response; idempotent for identical content."""
        meta = fetch.metadata
        partition = self._partition(fetch)
        checksum = meta.sha256[:_CHECKSUM_CHARS]

        existing = [
            key
            for key in self._store.list_keys(f"{partition}/")
            if key.endswith(f"-{checksum}.json")
        ]
        if existing:
            _LOG.info(
                "identical payload already archived, skipping",
                extra={"key": existing[0], "sha256": meta.sha256[:12]},
            )
            return ArchiveResult(
                key=existing[0],
                metadata_key=f"{existing[0].removesuffix('.json')}.meta.json",
                created=False,
            )

        stem = f"fetched_at={_compact_utc(meta.fetched_at_utc)}-{checksum}"
        key = f"{partition}/{stem}.json"
        metadata_key = f"{partition}/{stem}.meta.json"
        # Raw data is immutable: plain puts, never overwrite (rule 9).
        self._store.put_bytes(key, fetch.payload)
        self._store.put_bytes(
            metadata_key,
            json.dumps(meta.model_dump(), indent=1, sort_keys=True).encode("utf-8"),
        )
        _LOG.info(
            "archived raw payload",
            extra={"key": key, "bytes": len(fetch.payload), "sha256": meta.sha256[:12]},
        )
        return ArchiveResult(key=key, metadata_key=metadata_key, created=True)
