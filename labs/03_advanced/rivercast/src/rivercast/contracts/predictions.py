"""Prediction-record contract (PLAN.md Phase 9).

One record per issued forecast, persisted under the ``predictions`` object-
store zone so it can later be joined with the matured observation (once the
target time has passed) to compute delayed accuracy metrics (Phase 9's
"join-matured-predictions" / "calculate-delayed-metrics" pipeline steps,
extended by Phase 12's monitoring). ``actual_cm``/``error_cm`` start unset
and are filled in by :func:`rivercast.monitoring.delayed.join_matured_predictions`
once a real observation exists at ``target_time_utc`` — the record is never
rewritten before that, only extended.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PredictionRecord(_FrozenModel):
    """One forecast, as issued by ``components.forecast`` (PLAN.md Phase 9 schema)."""

    prediction_id: str
    issued_at_utc: str
    target_time_utc: str
    horizon_hours: int
    target_station_uuid: str
    prediction_cm: float
    model_name: str
    model_version: str
    model_alias: str
    dataset_id: str | None
    feature_version: int
    input_snapshot_uri: str | None = None
    created_by_pipeline_run: str | None = None


class MaturedPrediction(_FrozenModel):
    """A :class:`PredictionRecord` joined with its realized observation.

    ``actual_cm`` is ``None`` when no hourly observation exists yet at
    ``target_time_utc`` (rows with ``is_missing=True`` on the canonical
    grid) — the join records that explicitly rather than guessing a value
    (rule 13: fail closed / never fabricate).
    """

    prediction: PredictionRecord
    actual_cm: float | None
    error_cm: float | None
    matured_at_utc: str

    @property
    def is_matured(self) -> bool:
        return self.actual_cm is not None
