"""MLflow tracking tests: URI resolution and one logged run (offline, sqlite)."""

from __future__ import annotations

from pathlib import Path

import mlflow
import pytest
from mlflow.client import MlflowClient

from rivercast.config import load_config
from rivercast.models.local_pipeline import run_training
from rivercast.models.tracking import log_training_run, resolve_tracking_uri


@pytest.fixture()
def config(configs_dir: Path):
    return load_config(configs_dir / "local.yaml")


@pytest.fixture()
def fixture_dir(lab_root: Path) -> Path:
    return lab_root / "data_fixtures" / "pegelonline"


def test_resolve_tracking_uri_prefers_env_var(
    config, lab_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.mlflow.tracking_uri_env_var, "sqlite:///explicit.db")
    assert resolve_tracking_uri(config, lab_root) == "sqlite:///explicit.db"


def test_resolve_tracking_uri_falls_back_to_default_under_storage_root(
    config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(config.mlflow.tracking_uri_env_var, raising=False)
    uri = resolve_tracking_uri(config, tmp_path)
    assert uri.startswith("sqlite:///")
    assert uri.endswith("mlflow.db")
    assert "artifacts" in uri  # local.yaml's storage.root


def test_resolve_tracking_uri_raises_when_no_default_configured(
    config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(config.mlflow.tracking_uri_env_var, raising=False)
    stripped = config.model_copy(
        update={"mlflow": config.mlflow.model_copy(update={"tracking_uri_default": None})}
    )
    with pytest.raises(ValueError, match="tracking_uri_default"):
        resolve_tracking_uri(stripped, tmp_path)


def test_log_training_run_creates_a_run_with_metrics_and_model(
    config, fixture_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(config.mlflow.tracking_uri_env_var, tracking_uri)

    result = run_training(config, fixture_dir, 6, "ridge", tmp_path / "models", seed=42)
    logged = log_training_run(config, tmp_path, result)

    assert logged.dataset_id == result.dataset_id
    assert logged.horizon_hours == 6
    assert logged.model_name == "ridge"

    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(logged.run_id)
    assert run.data.params["model_name"] == "ridge"
    assert run.data.params["horizon_hours"] == "6"
    assert run.data.metrics["test_mae_cm"] == pytest.approx(result.test_report.mae_cm)
    assert run.data.tags["dataset_id"] == result.dataset_id
    assert run.data.tags["validation_status"] == "pending"
    assert run.data.tags["deployment_status"] == "not_deployed"

    artifacts = {a.path for a in client.list_artifacts(logged.run_id)}
    assert "dataset_manifest.json" in artifacts
    assert "feature_list.json" in artifacts
    # mlflow 3.x logs the model as a "Logged Model" entity linked to the run
    # (run.outputs), not as a plain run artifact under list_artifacts.
    assert len(run.outputs.model_outputs) == 1


def test_log_training_run_model_signature_matches_features(
    config, fixture_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(config.mlflow.tracking_uri_env_var, tracking_uri)

    result = run_training(config, fixture_dir, 6, "ridge", tmp_path / "models", seed=42)
    logged = log_training_run(config, tmp_path, result)

    mlflow.set_tracking_uri(tracking_uri)
    loaded_model = mlflow.pyfunc.load_model(f"runs:/{logged.run_id}/model")
    assert loaded_model.metadata.signature is not None
    input_names = [i.name for i in loaded_model.metadata.signature.inputs.inputs]
    assert set(input_names) == set(result.candidate.feature_columns)
