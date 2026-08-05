"""Operational test: MLflow tracking server unreachable (PLAN.md Phase 15
operational test "MLflow unavailable").

Points a component at a real, unreachable HTTP tracking URI (nothing is
listening there) rather than mocking the MLflow client, so the assertion is
about actual failure behavior over the wire, not about what a mock was
told to do. Every component that talks to MLflow already runs inside a
broad ``try/except`` that turns any failure into ``status="failed"``
(rule 13: fail closed) -- this test exists to prove that behavior against
a real connection failure, not just against contrived exceptions.

``MLFLOW_HTTP_REQUEST_TIMEOUT``/``..._MAX_RETRIES`` are pinned low: an
unreachable *loopback* port (as opposed to a routable-but-down host) does
not send an immediate TCP RST on this platform, so the OS-level connect
itself can take the platform's full connect timeout, then MLflow's default
retry budget multiplies that -- observed taking several minutes with
MLflow's defaults. Bounding both keeps this a fast, deterministic unit
test instead of a slow flake magnet.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from components.deploy.component import run as deploy_run

from rivercast.config import load_config

# 127.0.0.1 on an unassigned high port: nothing is listening, and no DNS
# lookup delay or real server exists anywhere to accidentally hit.
_UNREACHABLE_TRACKING_URI = "http://127.0.0.1:1/"


@pytest.fixture()
def isolated_config_path(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    base_config = load_config(configs_dir / "base.yaml")
    monkeypatch.setenv(base_config.mlflow.tracking_uri_env_var, _UNREACHABLE_TRACKING_URI)

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


def test_deploy_fails_closed_when_mlflow_is_unreachable(
    isolated_config_path: Path, lab_root: Path
) -> None:
    result = deploy_run(
        config_path=isolated_config_path,
        lab_root=lab_root,
        registered_model_name="rivercast-kaub-6h",
        model_version="1",
        smoke_test_features={"x": 1.0},
    )
    assert result.status == "failed"
    assert "error" in result.metadata
