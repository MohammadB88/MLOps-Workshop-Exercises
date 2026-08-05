"""Unit tests for components.run_lock (PLAN.md Phase 15, offline)."""

from __future__ import annotations

from pathlib import Path

import pytest
from components.run_lock.component import acquire, release

from rivercast.config import load_config


@pytest.fixture()
def isolated_config_path(configs_dir: Path, tmp_path: Path) -> Path:
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


def test_acquire_then_acquire_by_another_run_fails(
    isolated_config_path: Path, lab_root: Path
) -> None:
    first = acquire(isolated_config_path, lab_root, "rivercast-data-ops", "run-1")
    assert first.status == "ok"

    second = acquire(isolated_config_path, lab_root, "rivercast-data-ops", "run-2")
    assert second.status == "failed"
    assert "run-1" in str(second.metadata["error"])


def test_acquire_release_acquire_by_a_new_run_succeeds(
    isolated_config_path: Path, lab_root: Path
) -> None:
    acquire(isolated_config_path, lab_root, "rivercast-data-ops", "run-1")
    released = release(isolated_config_path, lab_root, "rivercast-data-ops", "run-1")
    assert released.status == "ok"

    second = acquire(isolated_config_path, lab_root, "rivercast-data-ops", "run-2")
    assert second.status == "ok"


def test_release_is_idempotent(isolated_config_path: Path, lab_root: Path) -> None:
    acquire(isolated_config_path, lab_root, "rivercast-data-ops", "run-1")
    first = release(isolated_config_path, lab_root, "rivercast-data-ops", "run-1")
    second = release(isolated_config_path, lab_root, "rivercast-data-ops", "run-1")
    assert first.status == "ok"
    assert second.status == "ok"


def test_config_loads_with_the_component(isolated_config_path: Path) -> None:
    # Sanity check the fixture builds a loadable config, matching every
    # other component test's isolation pattern.
    load_config(isolated_config_path)
