"""Config loading tests. No network access (CLAUDE.md rule 3)."""

from pathlib import Path

import pytest
import yaml

from rivercast.config import ConfigError, load_config


def _write_overlay(tmp_path: Path, configs_dir: Path, override: dict) -> Path:
    """Create an overlay of the real base.yaml with the given override mapping."""
    overlay = {"extends": str(configs_dir / "base.yaml"), **override}
    path = tmp_path / "overlay.yaml"
    path.write_text(yaml.safe_dump(overlay), encoding="utf-8")
    return path


def test_local_config_is_valid(configs_dir: Path) -> None:
    config = load_config(configs_dir / "local.yaml")
    assert config.mode == "fixture"
    assert config.target_station == "KAUB"
    assert [s.name for s in config.stations] == ["MAINZ", "OESTRICH", "BINGEN", "KAUB"]
    assert config.horizons_hours == [6, 12]
    assert config.storage.backend == "local"
    assert config.time.canonical_timezone == "UTC"


def test_openshift_config_is_valid(configs_dir: Path) -> None:
    config = load_config(configs_dir / "openshift.yaml")
    assert config.storage.backend == "s3"
    assert config.storage.s3 is not None
    assert config.storage.s3.bucket == "rivercast"


def test_overlay_deep_merges_mappings(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(
        tmp_path,
        configs_dir,
        {"thresholds": {"retraining": {"min_new_labeled_rows": 999}}},
    )
    config = load_config(path)
    assert config.thresholds.retraining.min_new_labeled_rows == 999
    # Sibling thresholds from base.yaml survive the merge.
    assert config.thresholds.labels.match_tolerance_minutes == 30


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_invalid_yaml_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("stations: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(path)


def test_unknown_key_is_rejected(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(tmp_path, configs_dir, {"tresholds": {"typo": 1}})
    with pytest.raises(ConfigError, match="tresholds"):
        load_config(path)


def test_invalid_mode_names_the_field(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(tmp_path, configs_dir, {"mode": "production"})
    with pytest.raises(ConfigError, match="mode"):
        load_config(path)


def test_live_mode_requires_station_uuids(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(
        tmp_path,
        configs_dir,
        {
            "mode": "live",
            "target_station": "KAUB",
            "stations": [{"name": "KAUB", "water_body": "RHEIN", "uuid": None}],
        },
    )
    with pytest.raises(ConfigError, match="no resolved UUID"):
        load_config(path)


def test_live_mode_with_pinned_uuids_is_valid(tmp_path: Path, configs_dir: Path) -> None:
    # Since the Phase 2 spike pinned all UUIDs in base.yaml, live mode validates.
    path = _write_overlay(tmp_path, configs_dir, {"mode": "live"})
    assert load_config(path).mode == "live"


def test_target_station_must_be_configured(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(tmp_path, configs_dir, {"target_station": "KOBLENZ"})
    with pytest.raises(ConfigError, match="KOBLENZ"):
        load_config(path)


def test_every_horizon_needs_a_registered_model(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(tmp_path, configs_dir, {"horizons_hours": [6, 12, 24]})
    with pytest.raises(ConfigError, match=r"\[24\]"):
        load_config(path)


def test_value_bounds_must_be_ordered(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(
        tmp_path,
        configs_dir,
        {"thresholds": {"data_quality": {"value_bounds_cm": {"min": 10, "max": 5}}}},
    )
    with pytest.raises(ConfigError, match="min must be < max"):
        load_config(path)


def test_bad_station_uuid_is_rejected(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(
        tmp_path,
        configs_dir,
        {"stations": [{"name": "KAUB", "water_body": "RHEIN", "uuid": "not-a-uuid"}]},
    )
    with pytest.raises(ConfigError, match="not a valid UUID"):
        load_config(path)


def test_s3_backend_requires_s3_section(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(tmp_path, configs_dir, {"storage": {"backend": "s3"}})
    with pytest.raises(ConfigError, match="storage.s3 section is missing"):
        load_config(path)


def test_circular_extends_is_detected(tmp_path: Path) -> None:
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text("extends: b.yaml\n", encoding="utf-8")
    b.write_text("extends: a.yaml\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="circular"):
        load_config(a)


def test_unknown_timezone_is_rejected(tmp_path: Path, configs_dir: Path) -> None:
    path = _write_overlay(tmp_path, configs_dir, {"time": {"source_timezone": "Mars/Olympus"}})
    with pytest.raises(ConfigError, match="unknown IANA timezone"):
        load_config(path)
