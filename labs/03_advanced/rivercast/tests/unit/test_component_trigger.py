"""Unit tests for components.trigger (PLAN.md Phase 10, offline)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from components.fetch.component import run as fetch_run
from components.train.component import run as train_run
from components.transform.component import run as transform_run
from components.trigger.component import run as trigger_run

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
def low_threshold_config_path(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Same as isolated_config_path but with min_new_labeled_rows lowered so
    the fixture dataset's ~155-161 trainable rows clear the bar.
    """
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
thresholds:
  data_quality:
    max_source_staleness_minutes: 120
    resample_tolerance_minutes: 30
    max_short_gap_minutes: 180
    value_bounds_cm:
      min: -200
      max: 1500
  labels:
    match_tolerance_minutes: 30
  promotion:
    min_skill_vs_persistence: 0.0
    max_mae_regression_vs_champion_cm: 1.0
    max_slice_regression_fraction: 0.10
  retraining:
    min_new_labeled_rows: 10
""",
        encoding="utf-8",
    )
    return config_path


def _materialize_gold_dataset(config_path: Path, tmp_path: Path, lab_root: Path) -> str:
    config = load_config(config_path)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    for station in config.stations:
        assert station.uuid is not None
        fetch_run(
            config_path=config_path,
            lab_root=tmp_path,
            station_uuid=station.uuid,
            parameter=config.source.parameter,
            start=WINDOW_START,
            end=WINDOW_END,
            fixture_dir=fixture_dir,
        )
    transform_result = transform_run(
        config_path=config_path, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    dataset_id = str(transform_result.metadata["dataset_id"])
    return dataset_id.removeprefix("sha256:")[:12]


def test_trigger_skips_when_not_enough_labeled_rows(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """The real fixture window has 161/155 trainable rows for 6h/12h, both
    under the default min_new_labeled_rows=168 -- this is a real skip, not
    a contrived one.
    """
    dataset_short_id = _materialize_gold_dataset(isolated_config_path, tmp_path, lab_root)

    result = trigger_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
    )
    assert result.status == "ok"
    assert result.metadata["should_train"] is False
    assert "labeled rows" in result.metadata["reason"]


def test_trigger_proceeds_when_enough_labeled_rows_and_no_prior_run(
    low_threshold_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    dataset_short_id = _materialize_gold_dataset(low_threshold_config_path, tmp_path, lab_root)

    result = trigger_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
    )
    assert result.status == "ok"
    assert result.metadata["should_train"] is True
    assert result.metadata["labeled_row_count"] >= 10


def test_trigger_skips_when_a_run_for_the_same_dataset_already_exists(
    low_threshold_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    dataset_short_id = _materialize_gold_dataset(low_threshold_config_path, tmp_path, lab_root)

    train_result = train_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
    )
    assert train_result.status == "ok"

    result = trigger_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
    )
    assert result.status == "ok"
    assert result.metadata["should_train"] is False
    assert "already exists" in result.metadata["reason"]


def test_trigger_fails_closed_on_missing_dataset(
    isolated_config_path: Path, tmp_path: Path
) -> None:
    result = trigger_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        dataset_short_id="doesnotexist",
        horizon_hours=6,
    )
    assert result.status == "failed"
    assert "error" in result.metadata


def test_trigger_fails_closed_on_unconfigured_horizon(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    dataset_short_id = _materialize_gold_dataset(isolated_config_path, tmp_path, lab_root)
    result = trigger_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=99,
    )
    assert result.status == "failed"
    assert "no label column" in result.metadata["error"]
