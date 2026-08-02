"""Feature and dataset-manifest contracts (PLAN.md Phase 5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = 1
FEATURE_VERSION = 1


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DatasetManifest(_FrozenModel):
    """Lineage record for one generated training dataset (PLAN.md Phase 5)."""

    dataset_id: str  # "sha256:<hex>"
    created_at_utc: str
    source_start_utc: str
    source_end_utc: str
    target_station_uuid: str
    input_station_uuids: list[str]
    horizons_hours: list[int]
    row_count: int
    schema_version: int = SCHEMA_VERSION
    feature_version: int = FEATURE_VERSION
    source_checksums: list[str]
    code_commit: str | None
    image_digest: str | None = None

    @property
    def short_id(self) -> str:
        return self.dataset_id.removeprefix("sha256:")[:12]
