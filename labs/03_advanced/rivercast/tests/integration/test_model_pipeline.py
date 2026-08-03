"""``rivercast-model`` pipeline tests (PLAN.md Phase 10 acceptance criteria).

Two kinds of coverage:

1. The pipeline **compiles** to valid KFP YAML with the expected DAG shape
   (``test_pipeline_compiles_to_kfp_yaml``).
2. The plan's four required scenarios, exercised directly through the same
   ``components.*.run()`` functions the compiled ``@dsl.component`` wrappers
   call (``pipelines/model_pipeline.py``'s task functions are trivial
   pass-throughs to these):

   1. No new data -> pipeline skips.
   2. Candidate worse than champion -> registered/rejected, no deployment.
   3. Candidate better but deployment fails -> champion unchanged.
   4. Candidate passes and endpoint works -> champion changes.

Full DAG **execution** via ``kfp.local.SubprocessRunner`` could not be
verified from this Windows development environment (see
``docs/pipeline_components.md``) -- the same KFP/Windows shell
incompatibility documented for Phase 9 reproduces here too.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from components.common import ComponentResult, open_store
from components.evaluate.component import run as evaluate_run
from components.fetch.component import run as fetch_run
from components.promote.component import run as promote_run
from components.register.component import run as register_run
from components.train.component import run as train_run
from components.transform.component import run as transform_run
from components.trigger.component import run as trigger_run
from mlflow.client import MlflowClient

from rivercast.config import load_config
from rivercast.models.registry import get_champion
from rivercast.models.tracking import resolve_tracking_uri
from rivercast.storage import zone_key

WINDOW_START = datetime(2024, 8, 1, tzinfo=UTC)
WINDOW_END = datetime(2024, 8, 8, tzinfo=UTC)


@pytest.fixture()
def isolated_config_path(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Default thresholds -- the real fixture window (~155-161 trainable
    rows) is naturally under min_new_labeled_rows=168, exercising scenario 1
    for free.
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
""",
        encoding="utf-8",
    )
    return config_path


@pytest.fixture()
def low_threshold_config_path(
    configs_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """min_new_labeled_rows lowered so the fixture dataset clears the bar --
    used for scenarios 2-4, which need training to actually happen.
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


def _materialize_gold_dataset(config_path: Path, tmp_path: Path, lab_root: Path) -> tuple[str, str]:
    """Returns (dataset_short_id, full dataset_id)."""
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
    return dataset_id.removeprefix("sha256:")[:12], dataset_id


def test_pipeline_compiles_to_kfp_yaml(tmp_path: Path) -> None:
    from kfp import compiler
    from pipelines.model_pipeline import rivercast_model_pipeline

    output_path = tmp_path / "compiled.yaml"
    compiler.Compiler().compile(rivercast_model_pipeline, str(output_path))

    assert output_path.is_file()
    content = output_path.read_text(encoding="utf-8")
    assert "rivercast-model" in content
    assert "trigger-task" in content
    assert "train-task" in content
    assert "evaluate-task" in content
    assert "register-task" in content
    assert "promote-task" in content


def test_scenario_1_no_new_data_pipeline_skips(
    isolated_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 10 acceptance scenario 1."""
    dataset_short_id, _ = _materialize_gold_dataset(isolated_config_path, tmp_path, lab_root)

    result = trigger_run(
        config_path=isolated_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
    )
    assert result.status == "ok"
    assert result.metadata["should_train"] is False
    # The pipeline's dsl.If(trigger.outputs["should_train"] == True) means no
    # train/evaluate/register/promote task ever runs for this dataset.


def test_scenario_2_candidate_worse_than_champion_rejected_no_deployment(
    low_threshold_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 10 acceptance scenario 2: candidate worse than champion
    -> registered/rejected, no deployment. Uses hist-gradient-boosting at
    12h, which genuinely underperforms persistence on this fixture window
    (Phase 6 finding) -- a real rejection.
    """
    dataset_short_id, dataset_id = _materialize_gold_dataset(
        low_threshold_config_path, tmp_path, lab_root
    )

    train_result = train_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=12,
        model_name="hist-gradient-boosting",
    )
    assert train_result.status == "ok"

    register_result = register_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        run_id=str(train_result.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=12,
        model_name="hist-gradient-boosting",
    )
    assert register_result.status == "ok"
    registered_model_name = str(register_result.metadata["registered_model_name"])
    model_version = str(register_result.metadata["model_version"])

    promote_result = promote_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        registered_model_name=registered_model_name,
        model_version=model_version,
        test_mae_cm=float(train_result.metadata["test_mae_cm"]),
        test_rmse_cm=float(train_result.metadata["test_mae_cm"]) * 1.2,
        test_persistence_mae_cm=6.17,
        test_skill_vs_persistence=float(train_result.metadata["test_skill_vs_persistence"]),
        smoke_test_features={"kaub_level_t": 100.0},
    )
    assert promote_result.status == "ok"
    assert promote_result.metadata["approved"] is False
    assert promote_result.metadata["promoted"] is False

    tracking_uri = resolve_tracking_uri(load_config(low_threshold_config_path), tmp_path)
    client = MlflowClient(tracking_uri=tracking_uri)
    fetched = client.get_model_version(registered_model_name, model_version)
    assert fetched.tags["validation_status"] == "rejected"
    assert get_champion(client, registered_model_name) is None


def test_scenario_3_candidate_better_but_deployment_fails_champion_unchanged(
    low_threshold_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 10 acceptance scenario 3."""
    dataset_short_id, dataset_id = _materialize_gold_dataset(
        low_threshold_config_path, tmp_path, lab_root
    )

    config = load_config(low_threshold_config_path)
    store = open_store(config, tmp_path)
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    feature_columns = [
        c for c in dataset.columns if not c.startswith("target_level_") and c != "issue_time_utc"
    ]
    smoke_row = dataset.iloc[-1][feature_columns].fillna(0.0)
    working_smoke_features = {
        col: int(smoke_row[col]) if col.startswith("missing_") else float(smoke_row[col])
        for col in feature_columns
    }

    # First candidate: promote cleanly to bootstrap a champion.
    first_train = train_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
        seed=42,
    )
    assert first_train.status == "ok"
    first_register = register_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        run_id=str(first_train.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=6,
        model_name="ridge",
    )
    first_promote = promote_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        registered_model_name=str(first_register.metadata["registered_model_name"]),
        model_version=str(first_register.metadata["model_version"]),
        test_mae_cm=float(first_train.metadata["test_mae_cm"]),
        test_rmse_cm=float(first_train.metadata["test_mae_cm"]) * 1.2,
        test_persistence_mae_cm=3.24,
        test_skill_vs_persistence=float(first_train.metadata["test_skill_vs_persistence"]),
        smoke_test_features=working_smoke_features,
    )
    assert first_promote.metadata["promoted"] is True

    tracking_uri = resolve_tracking_uri(load_config(low_threshold_config_path), tmp_path)
    client = MlflowClient(tracking_uri=tracking_uri)
    registered_model_name = str(first_register.metadata["registered_model_name"])
    champion_before = get_champion(client, registered_model_name)
    assert champion_before is not None
    assert str(champion_before.version) == str(first_register.metadata["model_version"])

    # Second candidate: same seed/data (ties the champion, so gates pass),
    # but its smoke-test payload deliberately omits every feature column the
    # model needs, so components.deploy's prediction call fails and the
    # champion must not move (rule 14).
    second_train = train_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
        seed=7,
    )
    second_register = register_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        run_id=str(second_train.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=6,
        model_name="ridge",
    )
    second_promote = promote_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        registered_model_name=str(second_register.metadata["registered_model_name"]),
        model_version=str(second_register.metadata["model_version"]),
        test_mae_cm=float(second_train.metadata["test_mae_cm"]),
        test_rmse_cm=float(second_train.metadata["test_mae_cm"]) * 1.2,
        test_persistence_mae_cm=3.24,
        test_skill_vs_persistence=float(second_train.metadata["test_skill_vs_persistence"]),
        smoke_test_features={"this_column_does_not_exist": 1.0},
    )
    assert second_promote.status == "ok"
    assert second_promote.metadata["approved"] is True
    assert second_promote.metadata["promoted"] is False

    champion_after = get_champion(client, registered_model_name)
    assert champion_after is not None
    assert champion_after.version == champion_before.version  # unchanged
    fetched = client.get_model_version(
        registered_model_name, str(second_register.metadata["model_version"])
    )
    assert fetched.tags["deployment_status"] == "failed"


def test_scenario_4_candidate_passes_and_endpoint_works_champion_changes(
    low_threshold_config_path: Path, tmp_path: Path, lab_root: Path
) -> None:
    """PLAN.md Phase 10 acceptance scenario 4."""
    dataset_short_id, dataset_id = _materialize_gold_dataset(
        low_threshold_config_path, tmp_path, lab_root
    )

    trigger_result = trigger_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
    )
    assert trigger_result.status == "ok"
    assert trigger_result.metadata["should_train"] is True

    train_result = train_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_name="ridge",
    )
    assert train_result.status == "ok"

    evaluate_result = _evaluate(low_threshold_config_path, tmp_path, dataset_short_id, train_result)

    register_result = register_run(
        config_path=low_threshold_config_path,
        lab_root=tmp_path,
        run_id=str(train_result.metadata["mlflow_run_id"]),
        dataset_id=dataset_id,
        horizon_hours=6,
        model_name="ridge",
    )
    assert register_result.status == "ok"
    registered_model_name = str(register_result.metadata["registered_model_name"])
    model_version = str(register_result.metadata["model_version"])

    # A real, working smoke-test feature row pulled from the gold dataset.
    config = load_config(low_threshold_config_path)
    store = open_store(config, tmp_path)
    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    feature_columns = [
        c for c in dataset.columns if not c.startswith("target_level_") and c != "issue_time_utc"
    ]
    smoke_row = dataset.iloc[-1][feature_columns].fillna(0.0)
    smoke_features = {
        col: int(smoke_row[col]) if col.startswith("missing_") else float(smoke_row[col])
        for col in feature_columns
    }

    promote_result = promote_run(
        config_path=low_threshold_config_path,
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
    assert promote_result.metadata["approved"] is True
    assert promote_result.metadata["promoted"] is True

    tracking_uri = resolve_tracking_uri(config, tmp_path)
    client = MlflowClient(tracking_uri=tracking_uri)
    champion = get_champion(client, registered_model_name)
    assert champion is not None
    assert str(champion.version) == str(model_version)


def _evaluate(
    config_path: Path, tmp_path: Path, dataset_short_id: str, train_result: ComponentResult
) -> ComponentResult:
    result = evaluate_run(
        config_path=config_path,
        lab_root=tmp_path,
        dataset_short_id=dataset_short_id,
        horizon_hours=6,
        model_path=Path(str(train_result.metadata["model_path"])),
        model_name="ridge",
        split_name="test",
    )
    assert result.status == "ok"
    return result
