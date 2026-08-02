"""Fetch → archive → parse, in that order (PLAN.md Phase 3).

The raw response is archived *before* parsing so a malformed payload is
preserved for diagnosis but never promoted downstream. Parsing failures are
reported in the outcome instead of raising, so scheduled ingestion can log
and continue with other stations while the bad payload stays quarantined in
bronze (rule 13: downstream consumers see only ``parsed_ok`` data).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rivercast.contracts.raw import Measurement
from rivercast.log import get_logger
from rivercast.sources.base import GaugeSource, MalformedResponseError, parse_measurements
from rivercast.storage.raw_archive import RawArchive

_LOG = get_logger("ingest")


@dataclass(frozen=True)
class IngestOutcome:
    station_uuid: str
    parameter: str
    archived_key: str
    archive_created: bool
    parsed_ok: bool
    measurements: list[Measurement]
    error: str | None


def ingest_window(
    source: GaugeSource,
    archive: RawArchive,
    station_uuid: str,
    parameter: str,
    start: datetime,
    end: datetime,
) -> IngestOutcome:
    """Fetch one station/parameter window, archive it immutably, then parse."""
    fetch = source.fetch_raw(station_uuid, parameter, start, end)
    result = archive.store(fetch)

    try:
        measurements = parse_measurements(fetch)
    except MalformedResponseError as exc:
        _LOG.error(
            "malformed payload archived but not promoted",
            extra={"archived_key": result.key, "station_uuid": station_uuid},
        )
        return IngestOutcome(
            station_uuid=station_uuid,
            parameter=parameter,
            archived_key=result.key,
            archive_created=result.created,
            parsed_ok=False,
            measurements=[],
            error=str(exc),
        )

    return IngestOutcome(
        station_uuid=station_uuid,
        parameter=parameter,
        archived_key=result.key,
        archive_created=result.created,
        parsed_ok=True,
        measurements=measurements,
        error=None,
    )
