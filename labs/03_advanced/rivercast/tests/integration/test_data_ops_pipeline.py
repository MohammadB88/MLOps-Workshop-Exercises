"""``rivercast-data-ops`` pipeline tests (PLAN.md Phase 9 acceptance criteria).

Two kinds of coverage:

1. The pipeline **compiles** to valid KFP YAML with the expected DAG shape
   (``test_pipeline_compiles_to_kfp_yaml``).
2. The **behavior** each pipeline step wires together is exercised directly
   through the same ``components.*.run()`` functions the compiled
   ``@dsl.component`` wrappers call (``pipelines/data_ops_pipeline.py``'s
   task functions are trivial pass-throughs to these, proven in
   ``tests/integration/test_components_end_to_end.py``'s component-level
   coverage; there is no independent orchestration logic to test other than
   the freshness gate, covered here).

Full DAG **execution** via ``kfp.local.SubprocessRunner`` could not be
verified from this Windows development environment (see
``docs/pipeline_components.md`` and this phase's PROGRESS.md note) -- KFP's
subprocess runner invokes the interpreter through a POSIX shell that
mis-resolves the Windows venv path, reproducing even for a trivial two-line
component with no RiverCast code involved. Re-verify in the Linux
JupyterLab workbench.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from components.common import open_store, read_json
from components.fetch.component import run as fetch_run
from components.forecast.component import run as forecast_run
from components.monitor.component import run as monitor_run
from components.transform.component import run as transform_run
from components.validate.component import run as validate_run
from mlflow.client import MlflowClient

from rivercast.config import load_config
from rivercast.contracts.hourly import HourlyObservation
from rivercast.contracts.predictions import PredictionRecord
from rivercast.models.local_pipeline import run_training
from rivercast.models.registry import assign_challenger, get_champion, register_candidate
from rivercast.models.tracking import log_training_run, resolve_tracking_uri
from rivercast.processing.delayed_metrics import calculate_delayed_metrics, join_matured_predictions

WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@pytest.fixture()
def isolated_config(configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base_config = load_config(configs_dir / "local.yaml")
    monkeypatch.delenv(base_config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(base_config.mlflow.tracking_uri_env_var, tracking_uri)

    config_path = tmp_path / "test_local.yaml"
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


def test_pipeline_compiles_to_kfp_yaml(tmp_path: Path) -> None:
    from kfp import compiler
    from pipelines.data_ops_pipeline import rivercast_data_ops_pipeline

    output_path = tmp_path / "compiled.yaml"
    compiler.Compiler().compile(rivercast_data_ops_pipeline, str(output_path))

    assert output_path.is_file()
    content = output_path.read_text(encoding="utf-8")
    assert "rivercast-data-ops" in content
    # DAG shape: fetch (ParallelFor), transform, validate, monitor, the
    # forecast conditional branch, and the delayed-metrics step all present.
    assert "transform-task" in content
    assert "validate-task" in content
    assert "monitor-task" in content
    assert "delayed-metrics-task" in content
    assert "forecast-task" in content


def test_fetch_two_identical_raw_fetches_do_not_duplicate_canonical_observations(
    isolated_config: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 9 acceptance criterion."""
    config = load_config(isolated_config)
    fixture_dir = lab_root / "data_fixtures" / "pegelonline"
    target = config.station(config.target_station)
    assert target.uuid is not None

    kwargs = {
        "config_path": isolated_config,
        "lab_root": tmp_path,
        "station_uuid": target.uuid,
        "parameter": config.source.parameter,
        "start": WINDOW_START,
        "end": WINDOW_END,
        "fixture_dir": fixture_dir,
    }
    first = fetch_run(**kwargs)
    second = fetch_run(**kwargs)
    assert first.output_keys == second.output_keys
    assert second.metadata["archive_created"] is False

    for station in config.stations:
        if station.name == target.name:
            continue
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
    assert transform_result.status == "ok"
    # Re-fetching the target station a second time before transform must not
    # have doubled its rows in the canonical hourly grid.
    silver_key = transform_result.output_keys[0]
    store = open_store(config, tmp_path)
    hourly = [HourlyObservation.model_validate(row) for row in read_json(store, silver_key)]
    target_hours = [h.hour_utc for h in hourly if h.station_uuid == target.uuid]
    assert len(target_hours) == len(set(target_hours))


def test_stale_source_prevents_forecast_generation(
    isolated_config: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 9 acceptance criterion: "A stale-source fixture
    prevents forecast generation." Mirrors what the pipeline's dsl.If gate
    enforces: forecast_task only runs when validate_task's status is "ok".
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

    far_future = WINDOW_END + timedelta(days=30)
    validate_result = validate_run(
        config_path=isolated_config, lab_root=tmp_path, silver_key=silver_key, now_utc=far_future
    )

    # This is exactly the condition the pipeline's dsl.If(validate.output ==
    # "ok") branches on; assert the orchestration contract directly.
    assert validate_result.status == "failed"
    should_forecast = validate_result.status == "ok"
    assert not should_forecast

    # monitor and delayed-metrics still run regardless (they report on the
    # data itself, not a forecast decision) -- the plan does not gate them.
    monitor_result = monitor_run(
        config_path=isolated_config, lab_root=tmp_path, silver_key=silver_key, now_utc=far_future
    )
    assert monitor_result.status == "ok"


def test_matured_predictions_receive_actual_values_and_errors(
    isolated_config: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 9 acceptance criterion: "Matured predictions receive
    actual values and errors." End-to-end: fetch -> transform -> train ->
    register -> promote -> forecast (persists a PredictionRecord) -> once
    "now" has passed target_time_utc, join_matured_predictions supplies the
    real observation and error.
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
    assert transform_result.status == "ok"
    silver_key = transform_result.output_keys[0]

    # Train + register + promote a champion for the 6h horizon directly
    # through the Phase 6/7 model functions (this test is about the Phase 9
    # join, not re-proving Phase 6/7's own training path).
    train_result = run_training(
        config=config,
        fixture_dir=fixture_dir,
        horizon_hours=6,
        model_name="ridge",
        models_dir=tmp_path / "models",
        seed=42,
    )
    logged_run = log_training_run(config, tmp_path, train_result)
    tracking_uri = resolve_tracking_uri(config, tmp_path)
    client = MlflowClient(tracking_uri=tracking_uri)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged_run)
    assign_challenger(client, "rivercast-kaub-6h", model_version)
    client.set_registered_model_alias("rivercast-kaub-6h", "champion", model_version.version)
    assert get_champion(client, "rivercast-kaub-6h") is not None

    # Issue a forecast for an issue time inside the fixture window so its
    # target_time_utc (issue_time + 6h) also falls inside the window and has
    # a real observation to mature against. missing_<station> columns are
    # logged as int64 in the model's inferred signature (0/1 flags only);
    # a plain dict.fromkeys(..., 0.0) would make them float64 and fail
    # mlflow's strict schema enforcement.
    issue_time = WINDOW_START + timedelta(hours=24)
    features: dict[str, float | int] = {
        column: 0 if column.startswith("missing_") else 0.0
        for column in train_result.candidate.feature_columns
    }
    forecast_result = forecast_run(
        config_path=isolated_config,
        lab_root=tmp_path,
        horizon_hours=6,
        issue_time=issue_time,
        features=features,
    )
    assert forecast_result.status == "ok"
    prediction_key = forecast_result.output_keys[0]

    store = open_store(config, tmp_path)
    prediction = PredictionRecord.model_validate(read_json(store, prediction_key))
    hourly = [HourlyObservation.model_validate(row) for row in read_json(store, silver_key)]

    # "now" is after target_time_utc (issue_time + 6h), so the prediction
    # has matured.
    now = issue_time + timedelta(hours=7)
    [matured] = join_matured_predictions([prediction], hourly, now_utc=now)

    assert matured.is_matured
    assert matured.actual_cm is not None
    assert matured.error_cm is not None

    metrics = calculate_delayed_metrics([matured], horizon_hours=6)
    assert metrics.n_matured == 1
    assert metrics.mae_cm is not None
