"""Silver-layer contracts: normalized and hourly-resampled observations.

``CanonicalObservation`` is the normalized (still native-cadence) record with
the full column set from PLAN.md Phase 4. ``HourlyObservation`` is the
resampled canonical-grid record used by every downstream phase; it carries an
explicit ``is_missing`` flag instead of ever being silently interpolated
(rule: large gaps stay explicit, never filled by default).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = 1


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError(f"must be timezone-aware UTC, got {value!r}")
    return value


class CanonicalObservation(_FrozenModel):
    """One normalized measurement at native (source) cadence."""

    station_uuid: str
    station_name: str = Field(min_length=1)
    water_body: str = Field(min_length=1)
    parameter: str = Field(min_length=1)
    observed_at_utc: datetime
    source_offset: str = Field(min_length=1)  # e.g. "+02:00", preserved verbatim
    value: float
    unit: str = Field(min_length=1)
    quality_status: str = Field(min_length=1)  # "ok" | "conflict"
    ingested_at_utc: datetime
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: int = SCHEMA_VERSION

    @field_validator("station_uuid")
    @classmethod
    def _valid_uuid(cls, value: str) -> str:
        UUID(value)
        return value

    @field_validator("observed_at_utc", "ingested_at_utc")
    @classmethod
    def _utc_aware(cls, value: datetime) -> datetime:
        return _require_utc(value)


class HourlyObservation(_FrozenModel):
    """One station's water level resampled onto the hourly canonical grid."""

    station_uuid: str
    station_name: str = Field(min_length=1)
    parameter: str = Field(min_length=1)
    hour_utc: datetime
    value: float | None
    is_missing: bool
    # UTC distance between hour_utc and the source reading used to fill it;
    # None when is_missing is True.
    source_lag_minutes: float | None = None
    schema_version: int = SCHEMA_VERSION

    @field_validator("station_uuid")
    @classmethod
    def _valid_uuid(cls, value: str) -> str:
        UUID(value)
        return value

    @field_validator("hour_utc")
    @classmethod
    def _utc_aware_and_on_grid(cls, value: datetime) -> datetime:
        value = _require_utc(value)
        if (value.minute, value.second, value.microsecond) != (0, 0, 0):
            raise ValueError(f"hour_utc must fall exactly on the hour, got {value!r}")
        return value
