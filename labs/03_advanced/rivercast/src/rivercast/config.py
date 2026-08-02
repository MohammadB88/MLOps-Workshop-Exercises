"""Typed configuration loading for RiverCast.

Configuration files are YAML with an optional ``extends: <relative path>`` key
for overlays (``local.yaml`` / ``openshift.yaml`` extend ``base.yaml``).
Overlay semantics: mappings deep-merge, scalars and lists replace. All values
are validated into frozen pydantic models; unknown keys are rejected so typos
fail loudly (CLAUDE.md rule 13: fail closed).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class ConfigError(Exception):
    """Raised for unreadable, unparseable, or invalid configuration."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetryConfig(_FrozenModel):
    max_attempts: int = Field(ge=1, le=10)
    backoff_initial_seconds: float = Field(gt=0)
    backoff_max_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def _backoff_ordered(self) -> RetryConfig:
        if self.backoff_max_seconds < self.backoff_initial_seconds:
            raise ValueError(
                "backoff_max_seconds must be >= backoff_initial_seconds "
                f"(got {self.backoff_max_seconds} < {self.backoff_initial_seconds})"
            )
        return self


class SourceConfig(_FrozenModel):
    name: str = Field(min_length=1)
    base_url: str = Field(pattern=r"^https://")
    parameter: str = Field(min_length=1)
    request_timeout_seconds: float = Field(gt=0)
    retry: RetryConfig


class TimeConfig(_FrozenModel):
    # Internal storage and computation are always UTC (CLAUDE.md rule 6).
    canonical_timezone: Literal["UTC"]
    source_timezone: str
    # Hourly canonical grid (ADR 0001); widen deliberately if that ever changes.
    grid_frequency: Literal["1h"]

    @field_validator("source_timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA timezone: {value!r}") from exc
        return value


class StationConfig(_FrozenModel):
    name: str = Field(min_length=1)
    water_body: str = Field(min_length=1)
    # None until the Phase 2 spike resolves and pins PEGELONLINE UUIDs.
    uuid: str | None = None

    @field_validator("uuid")
    @classmethod
    def _valid_uuid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            UUID(value)
        except ValueError as exc:
            raise ValueError(f"not a valid UUID: {value!r}") from exc
        return value


class StorageZones(_FrozenModel):
    bronze: str = Field(min_length=1)
    silver: str = Field(min_length=1)
    gold: str = Field(min_length=1)
    predictions: str = Field(min_length=1)
    reports: str = Field(min_length=1)
    models: str = Field(min_length=1)


class S3StorageConfig(_FrozenModel):
    bucket: str = Field(min_length=1)
    # Credentials and endpoint come from the environment (OpenShift data
    # connection); config stores only the variable names, never values.
    endpoint_url_env_var: str = "AWS_S3_ENDPOINT"
    access_key_env_var: str = "AWS_ACCESS_KEY_ID"
    secret_key_env_var: str = "AWS_SECRET_ACCESS_KEY"
    region_env_var: str = "AWS_DEFAULT_REGION"


class StorageConfig(_FrozenModel):
    backend: Literal["local", "s3"]
    root: str = Field(min_length=1)
    zones: StorageZones
    s3: S3StorageConfig | None = None

    @model_validator(mode="after")
    def _s3_requires_settings(self) -> StorageConfig:
        if self.backend == "s3" and self.s3 is None:
            raise ValueError("storage.backend is 's3' but the storage.s3 section is missing")
        return self


class MlflowConfig(_FrozenModel):
    tracking_uri_env_var: str = Field(min_length=1)
    # Used only when tracking_uri_env_var is unset in the environment -- keeps
    # fixture mode and CI self-sufficient without a live MLflow server. A
    # relative sqlite path is resolved against storage.root by the caller.
    tracking_uri_default: str | None = None
    experiment: str = Field(min_length=1)
    registered_models: dict[str, str]


class ValueBounds(_FrozenModel):
    min: float
    max: float

    @model_validator(mode="after")
    def _ordered(self) -> ValueBounds:
        if self.min >= self.max:
            raise ValueError(f"min must be < max (got min={self.min}, max={self.max})")
        return self


class DataQualityThresholds(_FrozenModel):
    max_source_staleness_minutes: int = Field(gt=0)
    resample_tolerance_minutes: int = Field(gt=0)
    max_short_gap_minutes: int = Field(gt=0)
    value_bounds_cm: ValueBounds


class LabelThresholds(_FrozenModel):
    match_tolerance_minutes: int = Field(gt=0)


class PromotionThresholds(_FrozenModel):
    min_skill_vs_persistence: float
    max_mae_regression_vs_champion_cm: float = Field(ge=0)
    max_slice_regression_fraction: float = Field(ge=0, le=1)


class RetrainingThresholds(_FrozenModel):
    min_new_labeled_rows: int = Field(gt=0)


class Thresholds(_FrozenModel):
    data_quality: DataQualityThresholds
    labels: LabelThresholds
    promotion: PromotionThresholds
    retraining: RetrainingThresholds


class RivercastConfig(_FrozenModel):
    schema_version: int = Field(ge=1)
    feature_version: int = Field(ge=1)
    # Fixture mode is the default for workshops and CI (CLAUDE.md rule 15).
    mode: Literal["fixture", "live"]
    time: TimeConfig
    source: SourceConfig
    target_station: str = Field(min_length=1)
    stations: list[StationConfig] = Field(min_length=1)
    horizons_hours: list[int] = Field(min_length=1)
    storage: StorageConfig
    mlflow: MlflowConfig
    thresholds: Thresholds

    @field_validator("horizons_hours")
    @classmethod
    def _horizons_positive_unique(cls, value: list[int]) -> list[int]:
        if any(h <= 0 for h in value):
            raise ValueError(f"horizons must be positive hours, got {value}")
        if len(set(value)) != len(value):
            raise ValueError(f"horizons contain duplicates: {value}")
        return value

    @model_validator(mode="after")
    def _cross_checks(self) -> RivercastConfig:
        names = [s.name for s in self.stations]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate station names: {names}")
        if self.target_station not in names:
            raise ValueError(f"target_station {self.target_station!r} is not in stations {names}")
        missing_models = [
            h for h in self.horizons_hours if str(h) not in self.mlflow.registered_models
        ]
        if missing_models:
            raise ValueError(
                f"horizons {missing_models} have no entry in mlflow.registered_models "
                f"(keys: {sorted(self.mlflow.registered_models)})"
            )
        if self.mode == "live":
            unresolved = [s.name for s in self.stations if s.uuid is None]
            if unresolved:
                raise ValueError(
                    "mode is 'live' but these stations have no resolved UUID: "
                    f"{unresolved}. Run the data-viability spike (Phase 2) and pin "
                    "UUIDs before enabling live mode."
                )
        return self

    def station(self, name: str) -> StationConfig:
        for s in self.stations:
            if s.name == name:
                return s
        raise KeyError(name)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Mappings merge recursively; scalars and lists in ``override`` replace."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"configuration file not found: {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"{path} must contain a YAML mapping, got {type(loaded).__name__}")
    return loaded


def _resolve_extends(path: Path, seen: tuple[Path, ...] = ()) -> dict[str, Any]:
    path = path.resolve()
    if path in seen:
        chain = " -> ".join(str(p) for p in (*seen, path))
        raise ConfigError(f"circular 'extends' chain: {chain}")
    data = _read_yaml_mapping(path)
    parent_ref = data.pop("extends", None)
    if parent_ref is None:
        return data
    if not isinstance(parent_ref, str):
        raise ConfigError(f"{path}: 'extends' must be a relative path string")
    parent = _resolve_extends(path.parent / parent_ref, (*seen, path))
    return _deep_merge(parent, data)


def _format_validation_error(path: Path, exc: ValidationError) -> str:
    lines = [f"invalid configuration in {path}:"]
    for err in exc.errors():
        location = ".".join(str(part) for part in err["loc"]) or "<root>"
        lines.append(f"  - {location}: {err['msg']}")
    return "\n".join(lines)


def load_config(path: str | Path) -> RivercastConfig:
    """Load and validate a configuration file, resolving ``extends`` overlays.

    Raises :class:`ConfigError` with a readable, per-field message on any
    problem; never returns a partially valid configuration.
    """
    resolved_path = Path(path)
    data = _resolve_extends(resolved_path)
    try:
        return RivercastConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(resolved_path, exc)) from exc
