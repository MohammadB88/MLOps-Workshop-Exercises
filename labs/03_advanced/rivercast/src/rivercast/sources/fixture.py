"""Deterministic fixture adapter over ``data_fixtures/pegelonline/``.

Serves the measurement windows committed by the Phase 2 spike through the
same :class:`GaugeSource` protocol and payload schema as the live adapter
(rule 5), fully offline. Determinism: identical inputs always produce
byte-identical payloads — ``fetched_at_utc`` is derived from the requested
window, not the wall clock.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from rivercast.contracts.raw import RawFetch, RawFetchMetadata, Station
from rivercast.gitinfo import current_commit
from rivercast.sources.base import SourceError

_STATIONS_FILE = "stations_rhein.json"


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float | str) else None


class FixtureGaugeSource:
    """Offline gauge source; implements the ``GaugeSource`` protocol."""

    source_name = "fixture"

    def __init__(self, fixture_dir: Path) -> None:
        self._dir = Path(fixture_dir)
        if not (self._dir / _STATIONS_FILE).is_file():
            raise SourceError(
                f"fixture directory {self._dir} has no {_STATIONS_FILE}; "
                "run scripts/source_spike.py --live to (re)create fixtures"
            )

    def _stations_raw(self) -> list[dict[str, object]]:
        loaded = json.loads((self._dir / _STATIONS_FILE).read_text(encoding="utf-8"))
        assert isinstance(loaded, list)
        return loaded

    def list_stations(self, water: str) -> list[Station]:
        if water.upper() != "RHEIN":
            raise SourceError(f"fixtures only cover RHEIN, requested {water!r}")
        return [
            Station(
                uuid=str(entry["uuid"]),
                shortname=str(entry["shortname"]),
                water="RHEIN",
                km=_optional_float(entry.get("km")),
                number=str(entry["number"]) if entry.get("number") is not None else None,
                agency=str(entry["agency"]) if entry.get("agency") is not None else None,
            )
            for entry in self._stations_raw()
        ]

    def _shortname_for(self, station_uuid: str) -> str:
        for entry in self._stations_raw():
            if entry["uuid"] == station_uuid:
                return str(entry["shortname"])
        raise SourceError(f"station uuid {station_uuid} not present in fixtures")

    def _all_rows_for(self, shortname: str) -> list[dict[str, object]]:
        """Union of every committed fixture window for one station, deduplicated."""
        candidates = [
            self._dir / "recent" / f"{shortname}.json",
            *sorted(self._dir.glob(f"historical/**/{shortname}.json")),
            *sorted(self._dir.glob(f"historical/*_{shortname}.json")),
        ]
        rows_by_timestamp: dict[str, dict[str, object]] = {}
        for path in candidates:
            if not path.is_file():
                continue
            for row in json.loads(path.read_text(encoding="utf-8")):
                rows_by_timestamp[str(row["timestamp"])] = row
        return list(rows_by_timestamp.values())

    def fetch_raw(
        self,
        station_uuid: str,
        parameter: str,
        start: datetime,
        end: datetime,
    ) -> RawFetch:
        if start.tzinfo is None or end.tzinfo is None:
            raise SourceError("start and end must be timezone-aware")
        if parameter != "W":
            raise SourceError(f"fixtures only cover parameter 'W', requested {parameter!r}")
        shortname = self._shortname_for(station_uuid)

        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)
        selected = [
            row
            for row in self._all_rows_for(shortname)
            if start_utc <= datetime.fromisoformat(str(row["timestamp"])).astimezone(UTC) < end_utc
        ]
        selected.sort(key=lambda row: datetime.fromisoformat(str(row["timestamp"])).astimezone(UTC))
        payload = json.dumps(selected, sort_keys=True, ensure_ascii=False).encode("utf-8")

        metadata = RawFetchMetadata(
            source=self.source_name,
            station_uuid=station_uuid,
            parameter=parameter,
            requested_start=start_utc.isoformat(),
            requested_end=end_utc.isoformat(),
            # Deterministic: derived from the request, never from the wall clock.
            fetched_at_utc=end_utc.isoformat(),
            http_status=200,
            etag=None,
            sha256=hashlib.sha256(payload).hexdigest(),
            code_commit=current_commit(),
        )
        return RawFetch(payload=payload, metadata=metadata)
