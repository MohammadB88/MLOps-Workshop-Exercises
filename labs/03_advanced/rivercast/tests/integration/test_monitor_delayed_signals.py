"""Delayed monitoring + retraining-signal acceptance tests (PLAN.md Phase 12).

Builds a real champion (train -> register -> promote), issues a real
forecast, matures it against a real hourly observation already present in
the fixture window, then exercises ``components.monitor`` end to end --
proving the retraining-decision artifact and drift/performance sections
populate from real data, not synthetic in-process objects (unlike
``tests/unit/test_monitoring_*.py``, which test the underlying modules in
isolation).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from components.common import open_store, read_json
from components.evaluate.component import run as evaluate_run
from components.fetch.component import run as fetch_run
from components.forecast.component import run as forecast_run
from components.monitor.component import run as monitor_run
from components.promote.component import run as promote_run
from components.register.component import run as register_run
from components.train.component import run as train_run
from components.transform.component import run as transform_run

from rivercast.config import load_config
from rivercast.storage import zone_key

WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@pytest.fixture()
def isolated_config(configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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


def _build_champion_and_forecast(
    config_path: Path, tmp_path: Path, lab_root: Path
) -> tuple[str, dict[str, float]]:
    """Fetch -> transform -> train -> register -> promote -> forecast for the
    6h horizon; returns (model_version, feature_row_used).
    """
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
    assert transform_result.status == "ok"
    dataset_id = str(transform_result.metadata["dataset_id"])
    dataset_short_id = dataset_id.removeprefix("sha256:")[:12]

    train_result = train_run(
        config_path=config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
        seed=42,
    )
    assert train_result.status == "ok"

    evaluate_result = evaluate_run(
        config_path=config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_path=Path(str(train_result.metadata["model_path"])),
        model_name="ridge",
        split_name="test",
    )
    assert evaluate_result.status == "ok"

    register_result = register_run(
        config_path=config_path,
        lab_root=tmp_path,
        run_id=str(train_result.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=6,
        model_name="ridge",
    )
    assert register_result.status == "ok"
    registered_model_name = str(register_result.metadata["registered_model_name"])
    model_version = str(register_result.metadata["model_version"])

    store = open_store(config, tmp_path)
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    feature_columns = [
        c for c in dataset.columns if not c.startswith("target_level_") and c != "issue_time_utc"
    ]
    # Use an early row so its 6h-ahead target time falls inside the fixture
    # window and a real hourly observation exists to mature the forecast
    # against (the very last row's target would be past WINDOW_END).
    early_row = dataset.iloc[10]
    issue_time = pd.Timestamp(early_row["issue_time_utc"])
    early_features = early_row[feature_columns].fillna(0.0)
    smoke_features: dict[str, float] = {
        column: int(early_features[column])
        if column.startswith("missing_")
        else float(early_features[column])
        for column in feature_columns
    }
    if issue_time.tzinfo is None:
        issue_time = issue_time.tz_localize(UTC)

    promote_result = promote_run(
        config_path=config_path,
        lab_root=tmp_path,
        registered_model_name=registered_model_name,
        model_version=model_version,
        test_mae_cm=float(evaluate_result.metadata["mae_cm"]),
        test_rmse_cm=float(evaluate_result.metadata["rmse_cm"]),
        test_persistence_mae_cm=3.24,
        test_skill_vs_persistence=float(evaluate_result.metadata["skill_vs_persistence"]),
        smoke_test_features=smoke_features,
    )
    assert promote_result.status == "ok"
    assert promote_result.metadata["promoted"] is True

    forecast_result = forecast_run(
        config_path=config_path,
        lab_root=tmp_path,
        horizon_hours=6,
        issue_time=issue_time.to_pydatetime(),
        features=smoke_features,
    )
    assert forecast_result.status == "ok", forecast_result.metadata

    return model_version, smoke_features


def test_monitor_reports_delayed_performance_for_a_matured_prediction(
    isolated_config: Path, tmp_path: Path, lab_root: Path
) -> None:
    """Plan acceptance: "Reports identify the exact model version and data
    window" -- once a forecast matures, monitor's delayed-performance
    section names the real champion version and reports a real MAE, not a
    placeholder.
    """
    model_version, _ = _build_champion_and_forecast(isolated_config, tmp_path, lab_root)

    config = load_config(isolated_config)
    store = open_store(config, tmp_path)
    transform_result = transform_run(
        config_path=isolated_config, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    silver_key = transform_result.output_keys[0]
    dataset_short_id = str(transform_result.metadata["dataset_id"]).removeprefix("sha256:")[:12]

    # now_utc well after the matured prediction's target_time but still
    # inside the fixture window, so the join finds a real observation.
    monitor_result = monitor_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        silver_key=silver_key,
        dataset_short_id=dataset_short_id,
        now_utc=WINDOW_END,
    )
    assert monitor_result.status == "ok"

    report = read_json(store, monitor_result.output_keys[0])
    horizons = {h["horizon_hours"]: h for h in report["delayed_by_horizon"]}
    assert 6 in horizons
    performance = horizons[6]["performance"]
    assert performance is not None
    assert performance["n_matured"] >= 1
    assert performance["mae_cm"] is not None

    retraining_signal = horizons[6]["retraining_signal"]
    assert retraining_signal is not None
    assert retraining_signal["reference_model_version"] == model_version


def test_monitor_reports_no_signal_before_any_prediction_matures(
    isolated_config: Path, tmp_path: Path, lab_root: Path
) -> None:
    """Plan acceptance: "Reports work with no labels" -- a monitor run before
    any forecast exists must still succeed, with an explicitly empty
    delayed-performance section rather than a crash.
    """
    config = load_config(isolated_config)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    for station in config.stations:
        assert station.uuid is not None
        fetch_run(
            config_path=isolated_config,
            lab_root=tmp_path,
            station_uuid=station.uuid,
            parameter=config.source.parameter,
            start=WINDOW_START,
            end=WINDOW_END,
            fixture_dir=fixture_dir,
        )
    transform_result = transform_run(
        config_path=isolated_config, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    silver_key = transform_result.output_keys[0]

    monitor_result = monitor_run(
        config_path=isolated_config, lab_root=tmp_path, silver_key=silver_key, now_utc=WINDOW_END
    )
    assert monitor_result.status == "ok"
    assert monitor_result.metadata["any_retraining_requested"] is False

    store = open_store(config, tmp_path)
    report = read_json(store, monitor_result.output_keys[0])
    for horizon_report in report["delayed_by_horizon"]:
        # No champion promoted yet for either horizon -- sections stay None,
        # not fabricated.
        assert horizon_report["performance"] is None
        assert horizon_report["retraining_signal"] is None


def test_drift_alone_does_not_bypass_promotion_gates(
    isolated_config: Path, tmp_path: Path, lab_root: Path
) -> None:
    """Plan acceptance: "A drift-only fixture does not bypass promotion
    gates" -- a monitor run that reports drift must not itself register,
    challenge, or promote any model version; promotion stays exclusively
    ``components.promote``'s job (ADR 0003).
    """
    model_version, _ = _build_champion_and_forecast(isolated_config, tmp_path, lab_root)

    config = load_config(isolated_config)
    transform_result = transform_run(
        config_path=isolated_config, lab_root=tmp_path, start=WINDOW_START, end=WINDOW_END
    )
    silver_key = transform_result.output_keys[0]
    dataset_short_id = str(transform_result.metadata["dataset_id"]).removeprefix("sha256:")[:12]

    from mlflow.client import MlflowClient

    from rivercast.models.registry import get_champion
    from rivercast.models.tracking import resolve_tracking_uri

    tracking_uri = resolve_tracking_uri(config, tmp_path)
    client = MlflowClient(tracking_uri=tracking_uri)
    registered_model_name = config.mlflow.registered_models["6"]
    champion_before = get_champion(client, registered_model_name)
    assert champion_before is not None
    assert str(champion_before.version) == model_version

    monitor_result = monitor_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        silver_key=silver_key,
        dataset_short_id=dataset_short_id,
        now_utc=WINDOW_END,
    )
    assert monitor_result.status == "ok"

    champion_after = get_champion(client, registered_model_name)
    assert champion_after is not None
    assert str(champion_after.version) == model_version
