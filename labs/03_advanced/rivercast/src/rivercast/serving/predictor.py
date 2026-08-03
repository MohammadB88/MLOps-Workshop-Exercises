"""Champion-model loading and scoring for the FastAPI serving layer (PLAN.md Phase 11).

Reuses the exact same registry/tracking code the ``forecast`` and ``deploy``
components already use (:mod:`rivercast.models.registry`,
:mod:`rivercast.models.tracking`) so serving never re-derives feature
contracts or champion-lookup logic independently (plan §Phase 11 "important
design rule").

A model version is loaded once per horizon and cached in the returned
:class:`Predictor`; ``/ready`` fails until the initial load succeeds. The
expected feature-column set for a horizon comes from the loaded MLflow
model's own signature -- never a hardcoded list -- so a schema mismatch in
the request is caught by comparing against what the model actually declares.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from mlflow.client import MlflowClient
from mlflow.entities.model_registry import ModelVersion
from mlflow.pyfunc import PyFuncModel

from rivercast.config import RivercastConfig, load_config
from rivercast.models.registry import get_champion
from rivercast.models.tracking import resolve_tracking_uri


class PredictorError(Exception):
    """Raised for any condition that must fail closed (CLAUDE.md rule 13)."""


@dataclass(frozen=True)
class LoadedChampion:
    horizon_hours: int
    registered_model_name: str
    model_version: str
    run_id: str
    dataset_id: str | None
    model: PyFuncModel
    feature_columns: list[str]
    feature_dtypes: dict[str, np.dtype]


def _feature_columns_from_signature(model: PyFuncModel) -> tuple[list[str], dict[str, np.dtype]]:
    signature = model.metadata.get_input_schema()
    if signature is None:
        raise PredictorError("loaded model has no input signature to validate requests against")
    dtypes = {name: dtype.to_pandas() for name, dtype in signature.input_types_dict().items()}
    return list(signature.input_names()), dtypes


def load_champion(
    client: MlflowClient, config: RivercastConfig, horizon_hours: int
) -> LoadedChampion:
    """Load the current champion for one horizon by MLflow alias.

    Fails closed with :class:`PredictorError` when the horizon is not
    configured, no champion has been promoted yet, or the artifact does not
    load -- never returns a partially-initialized champion.
    """
    registered_model_name = config.mlflow.registered_models.get(str(horizon_hours))
    if registered_model_name is None:
        raise PredictorError(
            f"horizon {horizon_hours} is not configured in mlflow.registered_models"
        )

    champion: ModelVersion | None = get_champion(client, registered_model_name)
    if champion is None:
        raise PredictorError(f"no champion is set yet for {registered_model_name!r}")
    if not champion.run_id:
        raise PredictorError(
            f"champion version {champion.version} of {registered_model_name!r} has no "
            "run_id; every promoted version must trace to a training run (CLAUDE.md rule 10)"
        )

    # runs:/<run_id>/model, not models:/<name>@champion: mirrors
    # components.common.model_run_uri -- loading via models:/ fails on
    # Windows with the currently pinned mlflow (see that helper's docstring).
    # src/rivercast must not import from components/ (dependency direction is
    # components -> rivercast, never the reverse), so this is intentionally
    # reimplemented rather than shared.
    model = mlflow.pyfunc.load_model(f"runs:/{champion.run_id}/model")
    feature_columns, feature_dtypes = _feature_columns_from_signature(model)

    return LoadedChampion(
        horizon_hours=horizon_hours,
        registered_model_name=registered_model_name,
        model_version=str(champion.version),
        run_id=champion.run_id,
        dataset_id=champion.tags.get("dataset_id"),
        model=model,
        feature_columns=feature_columns,
        feature_dtypes=feature_dtypes,
    )


class Predictor:
    """Loads and caches the champion model for each configured horizon.

    A fresh instance has loaded nothing yet; call :meth:`load_all` once at
    service startup. ``/ready`` should report unready until that succeeds for
    every configured horizon (fail closed rather than serving from a partial
    or stale cache).
    """

    def __init__(self, config: RivercastConfig, lab_root: Path) -> None:
        self._config = config
        self._lab_root = lab_root
        self._tracking_uri = resolve_tracking_uri(config, lab_root)
        self._champions: dict[int, LoadedChampion] = {}

    @property
    def config(self) -> RivercastConfig:
        return self._config

    def load_all(self) -> list[str]:
        """Attempt to (re)load the champion for every configured horizon.

        Returns the list of horizons that failed to load (empty list means
        fully ready). Does not raise -- callers decide how to report partial
        readiness.
        """
        mlflow.set_tracking_uri(self._tracking_uri)
        client = MlflowClient(tracking_uri=self._tracking_uri)
        failed: list[str] = []
        for horizon_hours in self._config.horizons_hours:
            try:
                self._champions[horizon_hours] = load_champion(client, self._config, horizon_hours)
            except Exception as exc:  # noqa: BLE001 -- any load failure means "not ready" for this horizon
                failed.append(f"{horizon_hours}h: {exc}")
        return failed

    def is_ready(self) -> bool:
        return len(self._champions) == len(self._config.horizons_hours)

    def loaded_horizons(self) -> list[int]:
        return sorted(self._champions)

    def champion_for(self, horizon_hours: int) -> LoadedChampion:
        champion = self._champions.get(horizon_hours)
        if champion is None:
            raise PredictorError(
                f"no champion loaded for horizon {horizon_hours}; configured horizons are "
                f"{self._config.horizons_hours}"
            )
        return champion

    def predict(self, horizon_hours: int, features: dict[str, float]) -> float:
        """Score one feature row against the horizon's champion.

        Fails closed: missing/extra columns or a non-finite prediction raise
        :class:`PredictorError` rather than silently returning a value.
        """
        champion = self.champion_for(horizon_hours)
        expected = set(champion.feature_columns)
        provided = set(features)
        missing = sorted(expected - provided)
        if missing:
            raise PredictorError(f"missing required features: {missing}")
        unexpected = sorted(provided - expected)
        if unexpected:
            raise PredictorError(f"unexpected features not used by this model: {unexpected}")

        row = pd.DataFrame([{col: features[col] for col in champion.feature_columns}])
        # The request arrives as JSON (dict[str, float]); recast to the
        # model's own declared dtypes (e.g. missing_<station> as int64) so
        # MLflow's strict schema enforcement doesn't reject an otherwise
        # valid float->int flag column (see predictor tests).
        row = row.astype(champion.feature_dtypes)
        prediction = float(np.asarray(champion.model.predict(row))[0])
        if not math.isfinite(prediction):
            raise PredictorError(f"model produced a non-finite prediction: {prediction}")
        return prediction


def build_predictor(config_path: str | Path, lab_root: str | Path) -> Predictor:
    config = load_config(config_path)
    return Predictor(config, Path(lab_root))
