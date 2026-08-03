"""Request/response schemas for the FastAPI serving layer (PLAN.md Phase 11)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PredictRequest(_FrozenModel):
    issue_time: datetime
    horizon_hours: int = Field(gt=0)
    features: dict[str, float]


class PredictResponse(_FrozenModel):
    target_station: str
    horizon_hours: int
    target_time: datetime
    prediction_cm: float
    model_name: str
    model_version: str
    dataset_id: str | None
    feature_version: int


class HealthResponse(_FrozenModel):
    status: str


class ReadyResponse(_FrozenModel):
    ready: bool
    loaded_horizons: list[int]
    errors: list[str]


class HorizonMetadata(_FrozenModel):
    horizon_hours: int
    model_name: str
    model_version: str
    feature_columns: list[str]


class MetadataResponse(_FrozenModel):
    target_station: str
    feature_version: int
    schema_version: int
    horizons: list[HorizonMetadata]
