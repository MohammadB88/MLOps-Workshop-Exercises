"""MLflow run retention-reporting tests (PLAN.md Phase 15 "artifact
retention"). Report-only, same rationale as ``rivercast.retention`` --
these tests confirm the candidate list, never a deletion."""

from __future__ import annotations

from pathlib import Path

import mlflow
import pytest
from mlflow.client import MlflowClient
from scripts.retention_report import report_mlflow_runs_older_than

from rivercast.config import load_config
from rivercast.models.local_pipeline import run_training
from rivercast.models.registry import (
    assign_challenger,
    promote_challenger_to_champion,
    register_candidate,
)
from rivercast.models.tracking import log_training_run


@pytest.fixture()
def fixture_dir(lab_root: Path) -> Path:
    return lab_root / "data_fixtures" / "pegelonline"


@pytest.fixture()
def isolated_config_path(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    base_config = load_config(configs_dir / "base.yaml")
    monkeypatch.delenv(base_config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(base_config.mlflow.tracking_uri_env_var, tracking_uri)
    mlflow.set_tracking_uri(tracking_uri)

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


def _logged_run(config_path: Path, fixture_dir: Path, tmp_path: Path, seed: int):
    config = load_config(config_path)
    result = run_training(
        config, fixture_dir, 6, "ridge", tmp_path / "models" / str(seed), seed=seed
    )
    return log_training_run(config, tmp_path, result)


def test_champion_run_is_never_a_retention_candidate(
    isolated_config_path: Path, fixture_dir: Path, tmp_path: Path
) -> None:
    config = load_config(isolated_config_path)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    client = MlflowClient(tracking_uri=tracking_uri)

    logged = _logged_run(isolated_config_path, fixture_dir, tmp_path, seed=42)
    model_name = config.mlflow.registered_models["6"]
    version = register_candidate(client, model_name, logged)
    assign_challenger(client, model_name, version)
    promote_challenger_to_champion(client, model_name, version, lambda _mv: True)

    report = report_mlflow_runs_older_than(isolated_config_path, tmp_path, retention_days=0)
    assert logged.run_id in report["protected_run_ids"]
    assert all(c["run_id"] != logged.run_id for c in report["candidates"])


def test_non_champion_old_run_is_a_candidate(
    isolated_config_path: Path, fixture_dir: Path, tmp_path: Path
) -> None:
    logged = _logged_run(isolated_config_path, fixture_dir, tmp_path, seed=42)

    report = report_mlflow_runs_older_than(isolated_config_path, tmp_path, retention_days=0)
    assert logged.run_id not in report["protected_run_ids"]
    assert any(c["run_id"] == logged.run_id for c in report["candidates"])


def test_recent_run_within_retention_window_is_not_a_candidate(
    isolated_config_path: Path, fixture_dir: Path, tmp_path: Path
) -> None:
    logged = _logged_run(isolated_config_path, fixture_dir, tmp_path, seed=42)

    report = report_mlflow_runs_older_than(isolated_config_path, tmp_path, retention_days=180)
    assert all(c["run_id"] != logged.run_id for c in report["candidates"])
