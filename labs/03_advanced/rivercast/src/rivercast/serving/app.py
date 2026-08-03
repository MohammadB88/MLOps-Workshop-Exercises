"""FastAPI serving application (PLAN.md Phase 11).

Exposes the current champion models for every configured horizon:

    GET  /health    -- liveness, no dependency on MLflow being reachable
    GET  /ready      -- readiness: every configured horizon has a loaded champion
    GET  /metadata   -- target station, schema/feature versions, per-horizon model info
    POST /predict    -- score one feature row with the champion for a horizon

The service does not recreate training features with different code (plan
§Phase 11 "important design rule"): callers supply the same feature columns
the model was trained on (see ``/metadata`` for the exact list per horizon),
and :class:`~rivercast.serving.predictor.Predictor` validates the request
against the model's own MLflow signature rather than a second, hand-written
schema.

Configuration is resolved once at process start from the ``RIVERCAST_CONFIG``
and ``RIVERCAST_LAB_ROOT`` environment variables (container-friendly; no CLI
flags needed for an ASGI app run under uvicorn/gunicorn).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from rivercast.serving.predictor import Predictor, PredictorError, build_predictor
from rivercast.serving.schemas import (
    HealthResponse,
    HorizonMetadata,
    MetadataResponse,
    PredictRequest,
    PredictResponse,
    ReadyResponse,
)

_CONFIG_PATH_ENV_VAR = "RIVERCAST_CONFIG"
_LAB_ROOT_ENV_VAR = "RIVERCAST_LAB_ROOT"


def _default_lab_root() -> Path:
    # src/rivercast/serving/app.py -> lab root is four parents up.
    return Path(__file__).resolve().parents[3]


def _resolve_predictor() -> Predictor:
    lab_root = Path(os.environ.get(_LAB_ROOT_ENV_VAR, _default_lab_root()))
    config_path = os.environ.get(_CONFIG_PATH_ENV_VAR, str(lab_root / "configs" / "local.yaml"))
    return build_predictor(config_path, lab_root)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.predictor = _resolve_predictor()
    app.state.load_errors = app.state.predictor.load_all()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="RiverCast serving",
        description=(
            "Educational river-level forecasting service (not a flood-warning product). "
            "Serves the current champion model per horizon."
        ),
        lifespan=_lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/ready", response_model=ReadyResponse)
    def ready() -> JSONResponse:
        predictor: Predictor = app.state.predictor
        response = ReadyResponse(
            ready=predictor.is_ready(),
            loaded_horizons=predictor.loaded_horizons(),
            errors=list(app.state.load_errors),
        )
        status_code = 200 if response.ready else 503
        return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))

    @app.get("/metadata", response_model=MetadataResponse)
    def metadata() -> MetadataResponse:
        predictor: Predictor = app.state.predictor
        config = predictor.config
        horizons = []
        for horizon_hours in predictor.loaded_horizons():
            champion = predictor.champion_for(horizon_hours)
            horizons.append(
                HorizonMetadata(
                    horizon_hours=horizon_hours,
                    model_name=champion.registered_model_name,
                    model_version=champion.model_version,
                    feature_columns=champion.feature_columns,
                )
            )
        return MetadataResponse(
            target_station=config.target_station,
            feature_version=config.feature_version,
            schema_version=config.schema_version,
            horizons=horizons,
        )

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        predictor: Predictor = app.state.predictor
        config = predictor.config
        if request.horizon_hours not in config.horizons_hours:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"horizon_hours must be one of {config.horizons_hours}, "
                    f"got {request.horizon_hours}"
                ),
            )
        try:
            champion = predictor.champion_for(request.horizon_hours)
            prediction_cm = predictor.predict(request.horizon_hours, request.features)
        except PredictorError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        target_time = request.issue_time + timedelta(hours=request.horizon_hours)
        return PredictResponse(
            target_station=config.target_station,
            horizon_hours=request.horizon_hours,
            target_time=target_time,
            prediction_cm=prediction_cm,
            model_name=champion.registered_model_name,
            model_version=champion.model_version,
            dataset_id=champion.dataset_id,
            feature_version=config.feature_version,
        )

    return app


app = create_app()
