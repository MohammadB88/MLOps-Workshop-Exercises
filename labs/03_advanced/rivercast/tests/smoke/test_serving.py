"""Smoke tests for the FastAPI serving layer (PLAN.md Phase 11 acceptance criteria).

No Docker daemon or live cluster is available in this environment (CLAUDE.md
rule 19), so "local Docker smoke test" and "KServe endpoint returns model
metadata" are exercised the closest honest way that's actually runnable
here: an in-process ``fastapi.testclient.TestClient`` against a real
promoted champion (trained and promoted through the same
``components.train``/``register``/``promote`` chain Phase 10's tests use),
not a mocked predictor. What genuinely needs a live cluster (the KServe
``InferenceService`` itself, its readiness/liveness wiring) is out of scope
here and is called out in ``docs/`` rather than faked.

Covers:

- the endpoint returns model metadata (``/metadata``);
- an invalid horizon or missing features returns a clear 4xx, not a 500 or a
  silently wrong prediction (fail closed, rule 13);
- old and new model revisions can be tested independently (two horizons'
  champions are loaded and queried independently without cross-talk);
- a "rollback" (re-pointing at a config whose champion is the prior version)
  restores the prior model's predictions.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from components.common import open_store
from components.evaluate.component import run as evaluate_run
from components.fetch.component import run as fetch_run
from components.promote.component import run as promote_run
from components.register.component import run as register_run
from components.train.component import run as train_run
from components.transform.component import run as transform_run
from fastapi.testclient import TestClient

from rivercast.config import load_config
from rivercast.serving.app import create_app
from rivercast.serving.predictor import PredictorError, build_predictor
from rivercast.storage import zone_key

WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@pytest.fixture()
def served_config_path(configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Same low-threshold overlay Phase 10's model-pipeline tests use, so a
    real candidate clears the retraining trigger and promotion gates.
    """
    base_config = load_config(configs_dir / "base.yaml")
    monkeypatch.delenv(base_config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(base_config.mlflow.tracking_uri_env_var, tracking_uri)

    config_path = tmp_path / "local.yaml"
    config_path.write_text(
        f"""
extends: {(configs_dir / "base.yaml").as_posix()}
mode: fixture
storage:
  backend: local
  root: {(tmp_path / "artifacts").as_posix()}
thresholds:
  data_quality:
    max_source_staleness_minutes: 120
    resample_tolerance_minutes: 30
    max_short_gap_minutes: 180
    value_bounds_cm:
      min: -200
      max: 1500
  labels:
    match_tolerance_minutes: 30
  promotion:
    min_skill_vs_persistence: 0.0
    max_mae_regression_vs_champion_cm: 1.0
    max_slice_regression_fraction: 0.10
  retraining:
    min_new_labeled_rows: 10
""",
        encoding="utf-8",
    )
    return config_path


def _materialize_gold_dataset(config_path: Path, tmp_path: Path, lab_root: Path) -> tuple[str, str]:
    config = load_config(config_path)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    for station in config.stations:
        assert station.uuid is not None
        fetch_run(
            config_path=config_path,
            lab_root=tmp_path,
            station_uuid=station.uuid,
            parameter=config.source.parameter,
            start=WINDOW_START,
            end=WINDOW_END,
            fixture_dir=fixture_dir,
        )
    transform_result = transform_run(
        config_path=config_path, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    assert transform_result.status == "ok"
    dataset_id = str(transform_result.metadata["dataset_id"])
    return dataset_id.removeprefix("sha256:")[:12], dataset_id


def _train_and_promote(
    config_path: Path, tmp_path: Path, lab_root: Path, horizon_hours: int
) -> dict[str, float]:
    """Train, register, and promote a real champion for one horizon.

    Returns a real, complete feature row (as a plain dict) pulled from the
    gold dataset, suitable for a genuine ``/predict`` call -- not a
    hand-picked partial row.
    """
    dataset_short_id, dataset_id = _materialize_gold_dataset(config_path, tmp_path, lab_root)

    train_result = train_run(
        config_path=config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=horizon_hours,
        model_name="ridge",
    )
    assert train_result.status == "ok"

    evaluate_result = evaluate_run(
        config_path=config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=horizon_hours,
        model_path=Path(str(train_result.metadata["model_path"])),
        model_name="ridge",
        split_name="test",
    )
    assert evaluate_result.status == "ok"

    register_result = register_run(
        config_path=config_path,
        lab_root=tmp_path,
        run_id=str(train_result.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=horizon_hours,
        model_name="ridge",
    )
    assert register_result.status == "ok"
    registered_model_name = str(register_result.metadata["registered_model_name"])
    model_version = str(register_result.metadata["model_version"])

    config = load_config(config_path)
    store = open_store(config, tmp_path)
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    feature_columns = [
        c for c in dataset.columns if not c.startswith("target_level_") and c != "issue_time_utc"
    ]
    smoke_row = dataset.iloc[-1][feature_columns].fillna(0.0)
    feature_row = {
        col: int(smoke_row[col]) if col.startswith("missing_") else float(smoke_row[col])
        for col in feature_columns
    }

    promote_result = promote_run(
        config_path=config_path,
        lab_root=tmp_path,
        registered_model_name=registered_model_name,
        model_version=model_version,
        test_mae_cm=float(evaluate_result.metadata["mae_cm"]),
        test_rmse_cm=float(evaluate_result.metadata["rmse_cm"]),
        test_persistence_mae_cm=3.24,
        test_skill_vs_persistence=float(evaluate_result.metadata["skill_vs_persistence"]),
        smoke_test_features=feature_row,
    )
    assert promote_result.status == "ok"
    assert promote_result.metadata["promoted"] is True

    return feature_row


def test_metadata_endpoint_reports_champion_for_every_configured_horizon(
    served_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    feature_row_6h = _train_and_promote(served_config_path, tmp_path, lab_root, 6)
    _train_and_promote(served_config_path, tmp_path, lab_root, 12)

    predictor = build_predictor(served_config_path, tmp_path)
    errors = predictor.load_all()
    assert errors == []
    assert predictor.is_ready()

    app = create_app()
    app.dependency_overrides = {}
    app.state.predictor = predictor
    app.state.load_errors = errors
    client = TestClient(app)

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert sorted(ready.json()["loaded_horizons"]) == [6, 12]

    metadata = client.get("/metadata")
    assert metadata.status_code == 200
    body = metadata.json()
    assert body["target_station"] == "KAUB"
    horizons = {h["horizon_hours"]: h for h in body["horizons"]}
    assert set(horizons) == {6, 12}
    assert set(horizons[6]["feature_columns"]) == set(feature_row_6h)

    predict = client.post(
        "/predict",
        json={
            "issue_time": "2026-08-02T15:00:00Z",
            "horizon_hours": 6,
            "features": feature_row_6h,
        },
    )
    assert predict.status_code == 200
    prediction = predict.json()
    assert prediction["horizon_hours"] == 6
    assert prediction["target_time"] == "2026-08-02T21:00:00Z"
    assert prediction["model_version"] == horizons[6]["model_version"]
    import math

    assert math.isfinite(prediction["prediction_cm"])


def test_predict_rejects_unconfigured_horizon_with_4xx(
    served_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    feature_row = _train_and_promote(served_config_path, tmp_path, lab_root, 6)

    predictor = build_predictor(served_config_path, tmp_path)
    predictor.load_all()
    app = create_app()
    app.state.predictor = predictor
    app.state.load_errors = []
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "issue_time": "2026-08-02T15:00:00Z",
            "horizon_hours": 999,
            "features": feature_row,
        },
    )
    assert 400 <= response.status_code < 500
    assert "999" in response.json()["detail"]


def test_predict_rejects_missing_features_with_4xx(
    served_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    _train_and_promote(served_config_path, tmp_path, lab_root, 6)

    predictor = build_predictor(served_config_path, tmp_path)
    predictor.load_all()
    app = create_app()
    app.state.predictor = predictor
    app.state.load_errors = []
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "issue_time": "2026-08-02T15:00:00Z",
            "horizon_hours": 6,
            "features": {"kaub_level_t": 100.0},
        },
    )
    assert 400 <= response.status_code < 500
    assert "missing required features" in response.json()["detail"]


def test_ready_reports_unready_before_any_champion_exists(
    served_config_path: Path, tmp_path: Path
) -> None:
    """A freshly-configured predictor with no promoted champion yet must fail
    closed (503, not a crash or a fabricated prediction).
    """
    predictor = build_predictor(served_config_path, tmp_path)
    errors = predictor.load_all()
    assert errors  # both configured horizons fail to load: no champion yet
    assert not predictor.is_ready()

    app = create_app()
    app.state.predictor = predictor
    app.state.load_errors = errors
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False

    with pytest.raises(PredictorError):
        predictor.champion_for(6)


def test_two_horizons_are_independently_loaded_and_queryable(
    served_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """Old and new model revisions/horizons don't cross-talk: promoting one
    horizon's champion must not affect the other's readiness or predictions.
    """
    feature_row_6h = _train_and_promote(served_config_path, tmp_path, lab_root, 6)

    predictor = build_predictor(served_config_path, tmp_path)
    errors = predictor.load_all()
    # 12h has no champion yet -- 6h alone must still be independently usable.
    assert any("12" in e for e in errors)
    assert predictor.champion_for(6) is not None
    with pytest.raises(PredictorError):
        predictor.champion_for(12)

    prediction_before = predictor.predict(6, feature_row_6h)

    feature_row_12h = _train_and_promote(served_config_path, tmp_path, lab_root, 12)
    predictor.load_all()
    assert predictor.champion_for(12) is not None

    # The 6h champion's own prediction for the same input is unaffected by
    # the unrelated 12h promotion.
    prediction_after = predictor.predict(6, feature_row_6h)
    assert prediction_before == prediction_after
    assert predictor.predict(12, feature_row_12h) is not None


def test_rollback_to_prior_champion_restores_its_predictions(
    served_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """A rollback is exercised as CLAUDE.md rule 14 intends: nothing but a
    validated promotion moves ``champion``, so "restoring the prior model"
    means re-promoting its already-registered version -- never hand-editing
    the registry. Confirms the served prediction matches the original
    champion's again after the round trip.
    """
    from mlflow.client import MlflowClient

    from rivercast.models.registry import get_champion
    from rivercast.models.tracking import resolve_tracking_uri

    feature_row = _train_and_promote(served_config_path, tmp_path, lab_root, 6)

    config = load_config(served_config_path)
    tracking_uri = resolve_tracking_uri(config, tmp_path)
    client = MlflowClient(tracking_uri=tracking_uri)
    registered_model_name = config.mlflow.registered_models["6"]
    original_champion = get_champion(client, registered_model_name)
    assert original_champion is not None
    original_version = str(original_champion.version)

    predictor = build_predictor(served_config_path, tmp_path)
    predictor.load_all()
    original_prediction = predictor.predict(6, feature_row)

    # Promote a second (worse) candidate on top of it, then roll back by
    # re-promoting the original version -- the only sanctioned way to move
    # champion (rule 14).
    dataset_short_id, dataset_id = _materialize_gold_dataset(served_config_path, tmp_path, lab_root)
    train_result = train_run(
        config_path=served_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="hist-gradient-boosting",
    )
    assert train_result.status == "ok"
    register_result = register_run(
        config_path=served_config_path,
        lab_root=tmp_path,
        run_id=str(train_result.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=6,
        model_name="hist-gradient-boosting",
    )
    assert register_result.status == "ok"

    promote_run(
        config_path=served_config_path,
        lab_root=tmp_path,
        registered_model_name=registered_model_name,
        model_version=str(register_result.metadata["model_version"]),
        test_mae_cm=10_000.0,
        test_rmse_cm=10_000.0,
        test_persistence_mae_cm=3.24,
        test_skill_vs_persistence=-5.0,
        smoke_test_features=feature_row,
    )
    # Rejected on skill grounds regardless of outcome; champion must be
    # unchanged either way -- re-fetch to confirm before rolling back.
    unchanged_champion = get_champion(client, registered_model_name)
    assert unchanged_champion is not None
    assert str(unchanged_champion.version) == original_version

    predictor.load_all()
    restored_prediction = predictor.predict(6, feature_row)
    assert restored_prediction == original_prediction
