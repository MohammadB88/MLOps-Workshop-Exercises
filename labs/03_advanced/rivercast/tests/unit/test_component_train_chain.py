"""Unit tests for components.train/evaluate/register/promote/forecast/deploy
failure and edge-case paths not already exercised by the full end-to-end
integration test (offline, sqlite MLflow store)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from components.deploy.component import run as deploy_run
from components.fetch.component import run as fetch_run
from components.forecast.component import run as forecast_run
from components.train.component import run as train_run
from components.transform.component import run as transform_run

from rivercast.config import load_config

WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@pytest.fixture()
def isolated_config_path(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
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
""",
        encoding="utf-8",
    )
    return config_path


@pytest.fixture()
def dataset_short_id(isolated_config_path: Path, tmp_path: Path, lab_root: Path) -> str:
    config = load_config(isolated_config_path)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    for station in config.stations:
        assert station.uuid is not None
        fetch_run(
            config_path=isolated_config_path,
            lab_root=tmp_path,
            station_uuid=station.uuid,
            parameter=config.source.parameter,
            start=WINDOW_START,
            end=WINDOW_END,
            fixture_dir=fixture_dir,
        )
    transform_result = transform_run(
        config_path=isolated_config_path, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    dataset_id = str(transform_result.metadata["dataset_id"])
    return dataset_id.removeprefix("sha256:")[:12]


def test_train_rejects_unconfigured_horizon(
    isolated_config_path: Path, tmp_path: Path, dataset_short_id: str
) -> None:
    result = train_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=99,
        model_name="ridge",
    )
    assert result.status == "failed"
    assert "not in configured horizons" in str(result.metadata["error"])


def test_forecast_fails_closed_when_no_champion_exists_yet(
    isolated_config_path: Path, tmp_path: Path, dataset_short_id: str
) -> None:
    # Train and log, but never register/promote -- no champion should exist.
    train_result = train_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
    )
    assert train_result.status == "ok"

    result = forecast_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        horizon_hours=6,
        issue_time=WINDOW_END,
        features={"kaub_level_t": 100.0},
    )
    assert result.status == "failed"
    assert "no champion" in str(result.metadata["error"])


def test_forecast_rejects_unconfigured_horizon(isolated_config_path: Path, tmp_path: Path) -> None:
    result = forecast_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        horizon_hours=99,
        issue_time=WINDOW_END,
        features={},
    )
    assert result.status == "failed"
    assert "no registered_models entry" in str(result.metadata["error"])


def test_deploy_fails_closed_on_a_nonexistent_model_version(
    isolated_config_path: Path, tmp_path: Path
) -> None:
    """No model has ever been registered -- deploy must fail cleanly rather
    than raise an unhandled exception (rule 13: fail closed).
    """
    result = deploy_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        registered_model_name="rivercast-kaub-6h",
        model_version="1",
        smoke_test_features={"kaub_level_t": 100.0},
    )
    assert result.status == "failed"
    assert "error" in result.metadata
