"""Unit tests for components.fetch (offline, fixture-mode)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from components.fetch.component import run as fetch_run

from rivercast.config import load_config

KAUB_UUID = "1d26e504-7f9e-480a-b52c-5932be6549ab"
WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


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


def test_fetch_archives_and_reports_measurement_count(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    result = fetch_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        station_uuid=KAUB_UUID,
        parameter="W",
        start=WINDOW_START,
        end=WINDOW_END,
        fixture_dir=fixture_dir,
    )
    assert result.status == "ok"
    assert result.metadata["measurement_count"] > 0
    assert result.metadata["archive_created"] is True
    assert len(result.output_keys) == 1


def test_fetch_is_idempotent_for_the_same_window(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    kwargs = {
        "config_path": isolated_config_path,
        "lab_root": tmp_path,
        "station_uuid": KAUB_UUID,
        "parameter": "W",
        "start": WINDOW_START,
        "end": WINDOW_END,
        "fixture_dir": fixture_dir,
    }
    first = fetch_run(**kwargs)
    second = fetch_run(**kwargs)
    assert first.output_keys == second.output_keys
    assert first.metadata["archive_created"] is True
    assert second.metadata["archive_created"] is False


def test_fetch_rejects_unknown_mode(isolated_config_path: Path, tmp_path: Path) -> None:
    config = load_config(isolated_config_path)
    assert config.mode == "fixture"  # sanity: base.yaml default is fixture

    bad_config_path = tmp_path / "bad.yaml"
    bad_config_path.write_text(
        isolated_config_path.read_text(encoding="utf-8").replace("mode: fixture", "mode: live"),
        encoding="utf-8",
    )
    # 'live' mode requires resolved UUIDs everywhere, which base.yaml already
    # has, so this should build a PegelOnlineSource -- but with no live
    # network access available in unit tests (rule 3), assert only that it
    # does NOT silently fall back to fixture behavior.
    from components.fetch.component import _build_source

    from rivercast.sources.pegelonline import PegelOnlineSource

    live_config = load_config(bad_config_path)
    source = _build_source("live", live_config, fixture_dir=None)
    assert isinstance(source, PegelOnlineSource)


def test_build_source_rejects_fixture_mode_without_fixture_dir(
    isolated_config_path: Path,
) -> None:
    from components.fetch.component import _build_source

    config = load_config(isolated_config_path)
    with pytest.raises(ValueError, match="fixture_dir is required"):
        _build_source("fixture", config, fixture_dir=None)
