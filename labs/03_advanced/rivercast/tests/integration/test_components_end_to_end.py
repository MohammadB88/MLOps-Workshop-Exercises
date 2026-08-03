"""End-to-end component chain: fetch -> transform -> validate -> train ->
register -> promote -> forecast -> deploy -> monitor (PLAN.md Phase 8).

Exercises every component as a plain Python function against a fully
isolated object store and MLflow sqlite tracking URI (no network, no shared
state with other tests or the real workbench artifacts) -- proving each
component works standalone and that they compose into the same pipeline
shape Phase 9 will wire into a real KFP DAG.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from components.deploy.component import run as deploy_run
from components.evaluate.component import run as evaluate_run
from components.fetch.component import run as fetch_run
from components.forecast.component import run as forecast_run
from components.monitor.component import run as monitor_run
from components.promote.component import run as promote_run
from components.register.component import run as register_run
from components.train.component import run as train_run
from components.transform.component import run as transform_run
from components.validate.component import run as validate_run

from rivercast.config import load_config
from rivercast.storage import create_object_store, zone_key

WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@pytest.fixture()
def isolated_config(configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A local.yaml-derived config pointed at an isolated storage root and
    MLflow sqlite store, so this test never touches ./artifacts.
    """
    base_config = load_config(configs_dir / "local.yaml")
    monkeypatch.delenv(base_config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(base_config.mlflow.tracking_uri_env_var, tracking_uri)

    config_path = tmp_path / "test_local.yaml"
    config_path.write_text(
        f"""
extends: {(configs_dir / "base.yaml").as_posix()}
mode: fixture
storage:
  backend: local
  root: {(tmp_path / "artifacts").as_posix()}
""",
        encoding="utf-8",
    )
    return config_path


def test_full_component_chain(isolated_config: Path, tmp_path: Path, lab_root: Path) -> None:
    config = load_config(isolated_config)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"

    # 1. fetch: archive raw measurements for every configured station.
    fetch_results = []
    for station in config.stations:
        assert station.uuid is not None
        result = fetch_run(
            config_path=isolated_config,
            lab_root=tmp_path,
            station_uuid=station.uuid,
            parameter=config.source.parameter,
            start=WINDOW_START,
            end=WINDOW_END,
            fixture_dir=fixture_dir,
        )
        assert result.status == "ok", result.metadata
        fetch_results.append(result)

    # 2. transform: bronze -> silver hourly grid -> gold dataset.
    transform_result = transform_run(
        config_path=isolated_config, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    assert transform_result.status == "ok", transform_result.metadata
    silver_key = transform_result.output_keys[0]
    dataset_id = str(transform_result.metadata["dataset_id"])
    dataset_short_id = dataset_id.removeprefix("sha256:")[:12]

    # 3. validate: quality gate over the silver window. now_utc anchored to
    # the fixture window (not the real wall clock) so the freshness check
    # doesn't fail as time passes.
    validate_result = validate_run(
        config_path=isolated_config, lab_root=tmp_path, silver_key=silver_key, now_utc=WINDOW_END
    )
    assert validate_result.status == "ok", validate_result.metadata
    assert validate_result.metadata["passed"] is True

    # 4. monitor: freshness/coverage summary over the same silver window.
    monitor_result = monitor_run(
        config_path=isolated_config, lab_root=tmp_path, silver_key=silver_key
    )
    assert monitor_result.status == "ok"
    assert monitor_result.metadata["missing_station_count"] == 0

    # 5. train: fit ridge for the 6h horizon, log to MLflow.
    train_result = train_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
        seed=42,
    )
    assert train_result.status == "ok", train_result.metadata
    run_id = str(train_result.metadata["mlflow_run_id"])
    model_path = Path(str(train_result.metadata["model_path"]))
    assert model_path.is_file()

    # 6. evaluate: re-score the saved artifact independently of training.
    evaluate_result = evaluate_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_path=model_path,
        model_name="ridge",
        split_name="test",
    )
    assert evaluate_result.status == "ok", evaluate_result.metadata
    assert evaluate_result.metadata["mae_cm"] == pytest.approx(
        float(train_result.metadata["test_mae_cm"])
    )

    # 7. register: create a model version from the MLflow run.
    register_result = register_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        run_id=run_id,
        dataset_id=dataset_id,
        horizon_hours=6,
        model_name="ridge",
    )
    assert register_result.status == "ok", register_result.metadata
    registered_model_name = str(register_result.metadata["registered_model_name"])
    model_version = str(register_result.metadata["model_version"])

    # 8. promote: first model for this horizon -> gates pass -> becomes champion.
    promote_result = promote_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        registered_model_name=registered_model_name,
        model_version=model_version,
        test_mae_cm=float(evaluate_result.metadata["mae_cm"]),
        test_rmse_cm=float(evaluate_result.metadata["rmse_cm"]),
        test_persistence_mae_cm=3.24,
        test_skill_vs_persistence=float(evaluate_result.metadata["skill_vs_persistence"]),
    )
    assert promote_result.status == "ok", promote_result.metadata
    assert promote_result.metadata["approved"] is True
    assert promote_result.metadata["promoted"] is True

    # 9. deploy: load the now-champion version and smoke-test it with a real
    # feature row pulled from the gold dataset (component outputs are kept
    # small and stable, so components don't echo feature columns themselves).
    store = create_object_store(
        config.storage.model_copy(update={"root": str(tmp_path / "artifacts")})
    )
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    feature_columns = [
        c for c in dataset.columns if not c.startswith("target_level_") and c != "issue_time_utc"
    ]
    smoke_row = dataset.iloc[-1][feature_columns].fillna(0.0)
    # missing_<station> columns are logged as int64 in the model's inferred
    # signature (they hold only 0/1 flags). The whole Series is float64 dtype
    # after fillna(), so assigning ints back into it just re-casts them to
    # float again; build the dict explicitly instead so those columns keep a
    # genuine Python int for a valid smoke-test payload against the strict
    # signature.
    smoke_features: dict[str, float | int] = {
        column: int(smoke_row[column])
        if column.startswith("missing_")
        else float(smoke_row[column])
        for column in feature_columns
    }

    deploy_result = deploy_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        registered_model_name=registered_model_name,
        model_version=model_version,
        smoke_test_features=smoke_features,
    )
    assert deploy_result.status == "ok", deploy_result.metadata
    assert deploy_result.metadata["smoke_test_passed"] is True

    # 10. forecast: issue one prediction from the now-champion model.
    forecast_result = forecast_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        horizon_hours=6,
        issue_time=WINDOW_END,
        features=smoke_features,
    )
    assert forecast_result.status == "ok", forecast_result.metadata
    assert forecast_result.metadata["model_alias"] == "champion"
    assert forecast_result.metadata["model_version"] == model_version
