"""Normalize raw measurements into the silver canonical schema (PLAN.md Phase 4).

A *conflict* is two different values reported for the same natural key
``(station_uuid, observed_at_utc, parameter)`` — e.g. a later fetch revising
an earlier reading. Resolution rule (documented, not implicit): **the record
from the most recently ingested raw fetch wins**, ties broken by the larger
value (arbitrary but deterministic) so output is reproducible. Both raw
observations remain in bronze; the losing record is retained here as a
:class:`ConflictRecord` for the data-quality report, not silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rivercast.contracts.hourly import CanonicalObservation
from rivercast.contracts.raw import Measurement

_UNIT_BY_PARAMETER = {"W": "cm"}


@dataclass(frozen=True)
class ConflictRecord:
    station_uuid: str
    observed_at_utc: datetime
    parameter: str
    kept_value: float
    kept_ingested_at_utc: datetime
    discarded_value: float
    discarded_ingested_at_utc: datetime


@dataclass(frozen=True)
class NormalizeResult:
    observations: list[CanonicalObservation]
    conflicts: list[ConflictRecord]


def _source_offset(timestamp_raw: str) -> str:
    """Extract the trailing UTC offset from an ISO-8601 timestamp string."""
    for sep in ("+", "-"):
        idx = timestamp_raw.rfind(sep)
        # A leading '-' (e.g. no offset present) would be idx <= 0; offsets
        # always appear after the time portion, i.e. after position 10.
        if idx > 10:
            return timestamp_raw[idx:]
    if timestamp_raw.endswith("Z"):
        return "+00:00"
    raise ValueError(f"timestamp has no recognizable UTC offset: {timestamp_raw!r}")


def normalize_measurements(
    measurements: list[Measurement],
    station_name: str,
    water_body: str,
    source_sha256: str,
    ingested_at_utc: datetime,
) -> NormalizeResult:
    """Normalize one station's measurements from a single raw fetch.

    Deduplicates by natural key ``(station_uuid, observed_at_utc, parameter)``;
    when the same key already exists in this batch with a different value, the
    conflict-resolution rule in the module docstring applies (larger value
    wins) and the conflict is recorded, never silently discarded.
    """
    if measurements and measurements[0].parameter not in _UNIT_BY_PARAMETER:
        raise ValueError(f"unknown parameter {measurements[0].parameter!r}; no unit mapping")

    kept: dict[tuple[str, datetime, str], CanonicalObservation] = {}
    conflicts: list[ConflictRecord] = []

    for measurement in measurements:
        key = (measurement.station_uuid, measurement.timestamp_utc, measurement.parameter)
        candidate = CanonicalObservation(
            station_uuid=measurement.station_uuid,
            station_name=station_name,
            water_body=water_body,
            parameter=measurement.parameter,
            observed_at_utc=measurement.timestamp_utc,
            source_offset=_source_offset(measurement.timestamp_raw),
            value=measurement.value,
            unit=_UNIT_BY_PARAMETER[measurement.parameter],
            quality_status="ok",
            ingested_at_utc=ingested_at_utc,
            source_sha256=source_sha256,
        )
        existing = kept.get(key)
        if existing is None:
            kept[key] = candidate
            continue
        if existing.value == candidate.value:
            continue  # exact duplicate, not a conflict
        # Deterministic tiebreak: keep the larger value (module docstring rule).
        winner, loser = (
            (candidate, existing) if candidate.value > existing.value else (existing, candidate)
        )
        kept[key] = winner.model_copy(update={"quality_status": "conflict"})
        conflicts.append(
            ConflictRecord(
                station_uuid=key[0],
                observed_at_utc=key[1],
                parameter=key[2],
                kept_value=winner.value,
                kept_ingested_at_utc=winner.ingested_at_utc,
                discarded_value=loser.value,
                discarded_ingested_at_utc=loser.ingested_at_utc,
            )
        )

    ordered = sorted(kept.values(), key=lambda obs: obs.observed_at_utc)
    return NormalizeResult(observations=ordered, conflicts=conflicts)
