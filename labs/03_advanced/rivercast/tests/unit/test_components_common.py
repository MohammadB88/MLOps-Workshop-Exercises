"""Tests for components/common.py: the shared result envelope and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from components.common import ComponentResult, emit, open_store, write_json

from rivercast.config import load_config


def test_component_result_to_json_round_trips() -> None:
    result = ComponentResult(
        component="fetch",
        status="ok",
        output_keys=["bronze/a.json"],
        metadata={"n": 3},
        code_commit="abc123",
    )
    payload = result.to_json()
    assert '"component": "fetch"' in payload
    assert '"status": "ok"' in payload
    assert '"bronze/a.json"' in payload


def test_emit_prints_and_does_not_exit_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
    emit(ComponentResult(component="fetch", status="ok"))
    out = capsys.readouterr().out
    assert '"status": "ok"' in out


def test_emit_exits_non_zero_on_failed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        emit(ComponentResult(component="fetch", status="failed", metadata={"error": "boom"}))
    assert excinfo.value.code == 1
    assert '"status": "failed"' in capsys.readouterr().out


def test_open_store_resolves_relative_root_under_lab_root(
    configs_dir: Path, lab_root: Path, tmp_path: Path
) -> None:
    config = load_config(configs_dir / "local.yaml")
    config = config.model_copy(
        update={"storage": config.storage.model_copy(update={"root": "artifacts"})}
    )
    store = open_store(config, tmp_path)
    write_json(store, "probe/x.json", {"a": 1})
    assert (tmp_path / "artifacts" / "probe" / "x.json").is_file()
