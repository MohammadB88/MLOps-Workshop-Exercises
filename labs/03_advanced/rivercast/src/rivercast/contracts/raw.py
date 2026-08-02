"""Typed records for the raw (bronze) layer — the source contract.

Both the live and the fixture adapter must produce exactly these types
(CLAUDE.md rule 5). Original source timestamps and offsets are preserved
verbatim in ``timestamp_raw`` while ``timestamp_utc`` is the internal UTC
axis (rules 6 and 7). ``RawFetchMetadata`` follows the required raw-metadata
schema from PLAN.md Phase 3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Station(_FrozenModel):
    uuid: str
    shortname: str = Field(min_length=1)
    water: str = Field(min_length=1)
    km: float | None = None
    number: str | None = None
    agency: str | None = None

    @field_validator("uuid")
    @classmethod
    def _valid_uuid(cls, value: str) -> str:
        UUID(value)
        return value


class Measurement(_FrozenModel):
    station_uuid: str
    parameter: str = Field(min_length=1)
    # Verbatim source timestamp including its original UTC offset (rule 7).
    timestamp_raw: str = Field(min_length=1)
    # The same instant on the internal UTC axis (rule 6).
    timestamp_utc: datetime
    value: float

    @field_validator("station_uuid")
    @classmethod
    def _valid_uuid(cls, value: str) -> str:
        UUID(value)
        return value

    @field_validator("timestamp_utc")
    @classmethod
    def _utc_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
            raise ValueError(f"timestamp_utc must be timezone-aware UTC, got {value!r}")
        return value


class RawFetchMetadata(_FrozenModel):
    """Provenance of one raw source response (PLAN.md Phase 3 metadata schema)."""

    source: str = Field(min_length=1)  # e.g. "pegelonline-rest-v2", "fixture"
    station_uuid: str
    parameter: str = Field(min_length=1)
    requested_start: str = Field(min_length=1)  # ISO-8601 as sent to the source
    requested_end: str = Field(min_length=1)
    fetched_at_utc: str = Field(min_length=1)
    http_status: int
    etag: str | None = None
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    code_commit: str | None = None
    schema_version: int = 1

    @field_validator("station_uuid")
    @classmethod
    def _valid_uuid(cls, value: str) -> str:
        UUID(value)
        return value


class RawFetch(_FrozenModel):
    """One raw response payload plus its provenance, ready for archiving."""

    payload: bytes
    metadata: RawFetchMetadata
