"""Gauge-source interface and the shared raw-payload parser.

Adapters return :class:`RawFetch` (payload bytes + provenance) so the caller
can archive the response *before* attempting to parse it — a malformed
response must be archived for diagnosis but never promoted downstream
(PLAN.md Phase 3). Parsing is one shared, pure function so the live and
fixture adapters cannot drift apart in output schema (rule 5).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from rivercast.contracts.raw import Measurement, RawFetch, Station


class SourceError(Exception):
    """Base error for gauge-source operations."""


class SourceTimeoutError(SourceError):
    """The source did not answer within the configured attempts."""


class MalformedResponseError(SourceError):
    """The payload does not conform to the measurement schema."""


@runtime_checkable
class GaugeSource(Protocol):
    def list_stations(self, water: str) -> list[Station]: ...

    def fetch_raw(
        self,
        station_uuid: str,
        parameter: str,
        start: datetime,
        end: datetime,
    ) -> RawFetch: ...


def parse_measurements(raw: RawFetch) -> list[Measurement]:
    """Parse an archived raw payload into typed measurements.

    Raises :class:`MalformedResponseError` with an explicit reason on any
    deviation from the expected ``[{"timestamp": ..., "value": ...}, ...]``
    schema; never returns partially parsed data (rule 13: fail closed).
    """
    try:
        rows = json.loads(raw.payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MalformedResponseError(
            f"payload for station {raw.metadata.station_uuid} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(rows, list):
        raise MalformedResponseError(
            f"payload for station {raw.metadata.station_uuid} is not a JSON array "
            f"(got {type(rows).__name__})"
        )

    measurements: list[Measurement] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or "timestamp" not in row or "value" not in row:
            raise MalformedResponseError(
                f"row {index} for station {raw.metadata.station_uuid} lacks "
                f"timestamp/value: {row!r}"
            )
        timestamp_raw = row["timestamp"]
        try:
            parsed = datetime.fromisoformat(timestamp_raw)
        except (TypeError, ValueError) as exc:
            raise MalformedResponseError(
                f"row {index}: unparseable timestamp {timestamp_raw!r}: {exc}"
            ) from exc
        if parsed.tzinfo is None:
            raise MalformedResponseError(
                f"row {index}: timestamp {timestamp_raw!r} has no UTC offset; "
                "refusing to guess the timezone"
            )
        try:
            measurements.append(
                Measurement(
                    station_uuid=raw.metadata.station_uuid,
                    parameter=raw.metadata.parameter,
                    timestamp_raw=timestamp_raw,
                    timestamp_utc=parsed.astimezone(UTC),
                    value=float(row["value"]),
                )
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise MalformedResponseError(f"row {index}: invalid measurement: {exc}") from exc
    return measurements
