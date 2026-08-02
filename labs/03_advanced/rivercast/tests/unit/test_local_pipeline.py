"""End-to-end local training run tests (offline, fixture-mode)."""

from pathlib import Path

import pytest

from rivercast.config import load_config
from rivercast.models.local_pipeline import materialize_fixture_dataset, run_training


@pytest.fixture()
def config(configs_dir: Path):
    return load_config(configs_dir / "local.yaml")


@pytest.fixture()
def fixture_dir(lab_root: Path) -> Path:
    return lab_root / "data_fixtures" / "pegelonline"


def test_materialize_fixture_dataset_has_labels_for_every_horizon(
    config, fixture_dir: Path
) -> None:
    dataset, manifest, feature_columns = materialize_fixture_dataset(config, fixture_dir)
    for horizon in config.horizons_hours:
        assert f"target_level_{horizon}h" in dataset.columns
    assert manifest.dataset_id.startswith("sha256:")
    assert "kaub_level_t" in feature_columns


def test_materialize_is_deterministic(config, fixture_dir: Path) -> None:
    _, manifest_a, _ = materialize_fixture_dataset(config, fixture_dir)
    _, manifest_b, _ = materialize_fixture_dataset(config, fixture_dir)
    assert manifest_a.dataset_id == manifest_b.dataset_id


def test_run_training_ridge_end_to_end(config, fixture_dir: Path, tmp_path: Path) -> None:
    result = run_training(
        config=config,
        fixture_dir=fixture_dir,
        horizon_hours=6,
        model_name="ridge",
        models_dir=tmp_path,
        seed=42,
    )
    assert result.model_path.is_file()
    assert result.n_train > 0 and result.n_validation > 0 and result.n_test > 0
    assert result.validation_report.n == result.n_validation
    assert result.test_report.n == result.n_test


def test_run_training_rejects_unconfigured_horizon(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="not in configured horizons"):
        run_training(
            config=config,
            fixture_dir=fixture_dir,
            horizon_hours=99,
            model_name="ridge",
            models_dir=tmp_path,
        )


def test_run_training_is_reproducible_for_same_seed(
    config, fixture_dir: Path, tmp_path: Path
) -> None:
    first = run_training(config, fixture_dir, 6, "ridge", tmp_path / "a", seed=42)
    second = run_training(config, fixture_dir, 6, "ridge", tmp_path / "b", seed=42)
    assert first.test_report.mae_cm == second.test_report.mae_cm
    assert first.dataset_id == second.dataset_id
