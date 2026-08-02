"""End-to-end train -> track -> register -> (optionally) promote tests (offline, sqlite)."""

from __future__ import annotations

from pathlib import Path

import pytest
from mlflow.client import MlflowClient

from rivercast.config import load_config
from rivercast.models.mlflow_pipeline import train_track_and_register
from rivercast.models.registry import get_champion
from rivercast.models.tracking import resolve_tracking_uri


@pytest.fixture()
def config(configs_dir: Path):
    return load_config(configs_dir / "local.yaml")


@pytest.fixture()
def fixture_dir(lab_root: Path) -> Path:
    return lab_root / "data_fixtures" / "pegelonline"


@pytest.fixture(autouse=True)
def _isolated_tracking_uri(config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(config.mlflow.tracking_uri_env_var, tracking_uri)


def test_first_model_bootstrap_registers_and_is_promotable(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    outcome = train_track_and_register(
        config, tmp_path, fixture_dir, 6, "ridge", tmp_path / "models", seed=42, promote=True
    )
    assert outcome.decision.approved
    assert outcome.promoted
    assert outcome.champion_model_version is None  # no champion existed before this run

    client = MlflowClient(tracking_uri=resolve_tracking_uri(config, tmp_path))
    champion = get_champion(client, outcome.registered_model_name)
    assert champion.version == outcome.model_version.version


def test_registering_without_promote_leaves_champion_unset(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    outcome = train_track_and_register(
        config, tmp_path, fixture_dir, 6, "ridge", tmp_path / "models", seed=42, promote=False
    )
    assert not outcome.promoted

    client = MlflowClient(tracking_uri=resolve_tracking_uri(config, tmp_path))
    assert get_champion(client, outcome.registered_model_name) is None
    fetched = client.get_model_version(outcome.registered_model_name, outcome.model_version.version)
    assert fetched.tags["validation_status"] == "approved"


def test_rejected_candidate_is_registered_but_not_promoted(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    # 12h hist-gradient-boosting underperforms persistence on the fixture
    # window (see reports/baseline/baseline_report.md) -- a real rejection,
    # not a contrived one.
    outcome = train_track_and_register(
        config,
        tmp_path,
        fixture_dir,
        12,
        "hist-gradient-boosting",
        tmp_path / "models",
        seed=42,
        promote=True,
    )
    assert not outcome.decision.approved
    assert not outcome.promoted

    client = MlflowClient(tracking_uri=resolve_tracking_uri(config, tmp_path))
    assert get_champion(client, outcome.registered_model_name) is None
    fetched = client.get_model_version(outcome.registered_model_name, outcome.model_version.version)
    assert fetched.tags["validation_status"] == "rejected"


def test_second_candidate_compares_against_the_real_champion(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    first = train_track_and_register(
        config, tmp_path, fixture_dir, 6, "ridge", tmp_path / "models" / "a", seed=42, promote=True
    )
    assert first.promoted

    second = train_track_and_register(
        config, tmp_path, fixture_dir, 6, "ridge", tmp_path / "models" / "b", seed=42, promote=True
    )
    # Same seed and data -> identical metrics -> zero regression -> approved.
    assert second.champion_model_version == first.model_version.version
    assert second.decision.approved
    assert second.promoted


def test_failed_deploy_smoke_test_does_not_move_champion(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    first = train_track_and_register(
        config, tmp_path, fixture_dir, 6, "ridge", tmp_path / "models" / "a", seed=42, promote=True
    )
    assert first.promoted

    second = train_track_and_register(
        config,
        tmp_path,
        fixture_dir,
        6,
        "ridge",
        tmp_path / "models" / "b",
        seed=42,
        promote=True,
        deploy_and_smoke_test=lambda _: False,
    )
    assert second.decision.approved  # gates passed
    assert not second.promoted  # but deployment validation failed

    client = MlflowClient(tracking_uri=resolve_tracking_uri(config, tmp_path))
    champion = get_champion(client, second.registered_model_name)
    assert champion.version == first.model_version.version  # unchanged
