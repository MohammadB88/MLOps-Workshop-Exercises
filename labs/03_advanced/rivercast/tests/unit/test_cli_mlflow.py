"""CLI tests for `rivercast train --track-mlflow` / `--promote` (Phase 7, offline)."""

from pathlib import Path

import pytest

from rivercast.cli import main
from rivercast.config import load_config


@pytest.fixture(autouse=True)
def _isolated_tracking_uri(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_config(configs_dir / "local.yaml")
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(config.mlflow.tracking_uri_env_var, tracking_uri)


def test_train_track_mlflow_registers_and_reports(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["train", "--horizon", "6", "--model", "ridge", "--track-mlflow"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "mlflow run:" in out
    assert "registered: rivercast-kaub-6h v" in out
    assert "promotion gates: PASS" in out
    assert "promoted to champion: False" in out


def test_train_promote_moves_champion_on_first_model(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["train", "--horizon", "6", "--model", "ridge", "--promote"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "promoted to champion: True" in out


def test_train_promote_reports_rejection_reason(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["train", "--horizon", "12", "--model", "hist-gradient-boosting", "--promote"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "promotion gates: REJECTED" in out
    assert "promoted to champion: False" in out
