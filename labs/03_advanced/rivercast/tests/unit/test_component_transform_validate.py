"""Unit tests for components.transform and components.validate (offline)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from components.common import open_store, write_json
from components.fetch.component import run as fetch_run
from components.transform.component import run as transform_run
from components.validate.component import run as validate_run

from rivercast.config import load_config
from rivercast.storage import zone_key

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


def test_transform_fails_closed_when_a_station_has_no_bronze_data(
    isolated_config_path: Path, tmp_path: Path
) -> None:
    """No fetch has run yet -> transform must fail, not silently build a
    dataset missing a required input station (rule 13: fail closed).
    """
    result = transform_run(
        config_path=isolated_config_path, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    assert result.status == "failed"
    assert "no bronze data" in str(result.metadata["error"])


def test_transform_succeeds_once_every_station_is_fetched(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    config = load_config(isolated_config_path)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    for station in config.stations:
        assert station.uuid is not None
        fetch_result = fetch_run(
            config_path=isolated_config_path,
            lab_root=tmp_path,
            station_uuid=station.uuid,
            parameter=config.source.parameter,
            start=WINDOW_START,
            end=WINDOW_END,
            fixture_dir=fixture_dir,
        )
        assert fetch_result.status == "ok"

    result = transform_run(
        config_path=isolated_config_path, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    assert result.status == "ok"
    assert len(result.output_keys) == 3  # silver, dataset, manifest
    assert result.metadata["row_count"] > 0


def test_validate_passes_on_a_full_transformed_window(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
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
    silver_key = transform_result.output_keys[0]

    # now_utc anchored to the fixture window (not the real wall clock) so
    # this test isn't sensitive to the freshness check as time passes.
    result = validate_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        silver_key=silver_key,
        now_utc=WINDOW_END,
    )
    assert result.status == "ok"
    assert result.metadata["passed"] is True


def test_validate_fails_closed_on_stale_target_station_data(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 9 acceptance criterion: "A stale-source fixture
    prevents forecast generation." now_utc is set far past the fixture
    window's newest reading, well beyond max_source_staleness_minutes.
    """
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
    silver_key = transform_result.output_keys[0]

    far_future = WINDOW_END + timedelta(days=30)
    result = validate_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        silver_key=silver_key,
        now_utc=far_future,
    )
    assert result.status == "failed"
    assert result.metadata["passed"] is False
    assert any(
        "freshness" in msg.lower() or "old" in msg.lower() for msg in result.metadata["errors"]
    )


def test_validate_fails_closed_on_missing_station_coverage(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """Simulates a silver window that's missing one station's data entirely
    -- validate must report status='failed', not a silent warning.
    """
    config = load_config(isolated_config_path)
    store = open_store(config, tmp_path)
    # Only one station's hourly rows -- the other three are "missing".
    target = config.station(config.target_station)
    silver_key = zone_key(config.storage.zones, "silver", "hourly", "window=incomplete.json")
    write_json(
        store,
        silver_key,
        [
            {
                "station_uuid": target.uuid,
                "station_name": target.name,
                "parameter": "W",
                "hour_utc": "2024-08-01T00:00:00+00:00",
                "value": 100.0,
                "is_missing": False,
                "source_lag_minutes": 0.0,
            }
        ],
    )

    result = validate_run(
        config_path=isolated_config_path, lab_root=tmp_path, silver_key=silver_key
    )
    assert result.status == "failed"
    assert result.metadata["passed"] is False
    assert any("station" in msg for msg in result.metadata["errors"])
