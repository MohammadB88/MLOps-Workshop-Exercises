"""Registry tests: bootstrap, idempotent registration, aliasing, promotion gates
and transaction, all against a local sqlite MLflow store (offline)."""

from __future__ import annotations

from pathlib import Path

import mlflow
import pytest
from mlflow.client import MlflowClient

from rivercast.config import load_config
from rivercast.models.evaluate import EvaluationReport, SliceMetric
from rivercast.models.local_pipeline import run_training
from rivercast.models.registry import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    assign_challenger,
    champion_test_report,
    evaluate_promotion_gates,
    get_champion,
    promote_challenger_to_champion,
    register_candidate,
    reject_candidate,
)
from rivercast.models.tracking import log_training_run


@pytest.fixture()
def config(configs_dir: Path):
    return load_config(configs_dir / "local.yaml")


@pytest.fixture()
def fixture_dir(lab_root: Path) -> Path:
    return lab_root / "data_fixtures" / "pegelonline"


@pytest.fixture()
def client(config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MlflowClient:
    monkeypatch.delenv(config.mlflow.tracking_uri_env_var, raising=False)
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv(config.mlflow.tracking_uri_env_var, tracking_uri)
    mlflow.set_tracking_uri(tracking_uri)  # also drives the fluent API (mlflow.start_run)
    return MlflowClient(tracking_uri=tracking_uri)


def _logged_run(config, fixture_dir: Path, tmp_path: Path, seed: int = 42):
    result = run_training(
        config, fixture_dir, 6, "ridge", tmp_path / "models" / str(seed), seed=seed
    )
    return log_training_run(config, tmp_path, result), result


# ---------------------------------------------------------------------------
# Registration: bootstrap and idempotency


def test_register_candidate_bootstraps_a_new_registered_model(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    assert str(model_version.version) == "1"
    assert client.get_registered_model("rivercast-kaub-6h") is not None


def test_register_candidate_is_idempotent_for_the_same_run(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    first = register_candidate(client, "rivercast-kaub-6h", logged)
    second = register_candidate(client, "rivercast-kaub-6h", logged)
    assert first.version == second.version


def test_register_candidate_creates_a_new_version_for_a_different_run(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged_a, _ = _logged_run(config, fixture_dir, tmp_path, seed=42)
    logged_b, _ = _logged_run(config, fixture_dir, tmp_path, seed=7)
    version_a = register_candidate(client, "rivercast-kaub-6h", logged_a)
    version_b = register_candidate(client, "rivercast-kaub-6h", logged_b)
    assert version_a.version != version_b.version


def test_register_candidate_tags_lineage(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    fetched = client.get_model_version("rivercast-kaub-6h", model_version.version)
    assert fetched.tags["dataset_id"] == logged.dataset_id
    assert fetched.tags["horizon_hours"] == "6"
    assert fetched.tags["validation_status"] == "pending"
    assert fetched.tags["deployment_status"] == "not_deployed"
    assert fetched.run_id == logged.run_id


# ---------------------------------------------------------------------------
# Champion bootstrap and alias lookup


def test_get_champion_returns_none_when_no_champion_exists(client: MlflowClient) -> None:
    client.create_registered_model("rivercast-kaub-6h")
    assert get_champion(client, "rivercast-kaub-6h") is None


def test_assign_challenger_and_read_back_by_alias(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    assign_challenger(client, "rivercast-kaub-6h", model_version)
    fetched = client.get_model_version_by_alias("rivercast-kaub-6h", CHALLENGER_ALIAS)
    assert fetched.version == model_version.version


# ---------------------------------------------------------------------------
# Promotion gates


def _report(mae: float, skill: float, slices: list[SliceMetric] | None = None) -> EvaluationReport:
    return EvaluationReport(
        model_name="ridge",
        horizon_hours=6,
        n=25,
        mae_cm=mae,
        rmse_cm=mae * 1.2,
        persistence_mae_cm=3.0,
        skill_vs_persistence=skill,
        slices=slices or [],
    )


def test_promotion_gate_approves_when_skill_beats_persistence_and_no_champion() -> None:
    decision = evaluate_promotion_gates(_report(1.0, 0.5), None, 0.0, 1.0, 0.10)
    assert decision.approved
    assert decision.reasons == []


def test_promotion_gate_rejects_when_skill_below_threshold() -> None:
    decision = evaluate_promotion_gates(_report(4.0, -0.3), None, 0.0, 1.0, 0.10)
    assert not decision.approved
    assert "skill_vs_persistence" in decision.reasons[0]


def test_promotion_gate_rejects_mae_regression_vs_champion() -> None:
    champion = _report(1.0, 0.6)
    candidate = _report(3.0, 0.1)  # regressed by 2cm, allowed only 1cm
    decision = evaluate_promotion_gates(candidate, champion, 0.0, 1.0, 0.10)
    assert not decision.approved
    assert any("regressed" in reason for reason in decision.reasons)


def test_promotion_gate_approves_small_mae_regression_within_tolerance() -> None:
    champion = _report(1.0, 0.6)
    candidate = _report(1.5, 0.5)  # regressed by 0.5cm, allowed up to 1cm
    decision = evaluate_promotion_gates(candidate, champion, 0.0, 1.0, 0.10)
    assert decision.approved


def test_promotion_gate_rejects_slice_regression_beyond_fraction() -> None:
    champion_slices = [SliceMetric("rising_falling", "rising", 10, mae_cm=1.0, rmse_cm=1.2)]
    candidate_slices = [SliceMetric("rising_falling", "rising", 10, mae_cm=2.0, rmse_cm=2.2)]
    champion = _report(1.0, 0.6, champion_slices)
    candidate = _report(1.0, 0.6, candidate_slices)  # headline ties; slice regresses 100%
    decision = evaluate_promotion_gates(candidate, champion, 0.0, 1.0, 0.10)
    assert not decision.approved
    assert any("slice" in reason for reason in decision.reasons)


# ---------------------------------------------------------------------------
# champion_test_report reconstruction from a logged run


def test_champion_test_report_reconstructs_metrics_from_the_run(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, result = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    assign_challenger(client, "rivercast-kaub-6h", model_version)
    client.set_registered_model_alias("rivercast-kaub-6h", CHAMPION_ALIAS, model_version.version)

    champion = get_champion(client, "rivercast-kaub-6h")
    report = champion_test_report(client, champion)

    assert report is not None
    assert report.mae_cm == pytest.approx(result.test_report.mae_cm)
    assert report.skill_vs_persistence == pytest.approx(result.test_report.skill_vs_persistence)


def test_champion_test_report_returns_none_for_run_missing_metrics(client: MlflowClient) -> None:
    client.create_registered_model("rivercast-kaub-6h")
    mlflow.set_experiment("rivercast")
    with mlflow.start_run() as run:
        pass
    mv = client.create_model_version("rivercast-kaub-6h", source="dummy", run_id=run.info.run_id)
    client.set_registered_model_alias("rivercast-kaub-6h", CHAMPION_ALIAS, mv.version)
    champion = get_champion(client, "rivercast-kaub-6h")
    assert champion_test_report(client, champion) is None


# ---------------------------------------------------------------------------
# Promotion transaction: reject / deploy-fail / success, champion untouched on failure


def test_reject_candidate_tags_rejected_and_never_gets_champion(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    reject_candidate(client, "rivercast-kaub-6h", model_version)
    fetched = client.get_model_version("rivercast-kaub-6h", model_version.version)
    assert fetched.tags["validation_status"] == "rejected"
    assert get_champion(client, "rivercast-kaub-6h") is None


def test_promote_challenger_to_champion_succeeds_on_passing_smoke_test(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    assign_challenger(client, "rivercast-kaub-6h", model_version)

    promoted = promote_challenger_to_champion(
        client, "rivercast-kaub-6h", model_version, lambda _: True
    )

    assert promoted
    champion = get_champion(client, "rivercast-kaub-6h")
    assert champion.version == model_version.version
    fetched = client.get_model_version("rivercast-kaub-6h", model_version.version)
    assert fetched.tags["validation_status"] == "approved"
    assert fetched.tags["deployment_status"] == "deployed"


def test_promote_challenger_to_champion_leaves_champion_unchanged_on_failed_smoke_test(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    first_logged, _ = _logged_run(config, fixture_dir, tmp_path, seed=42)
    first_version = register_candidate(client, "rivercast-kaub-6h", first_logged)
    assign_challenger(client, "rivercast-kaub-6h", first_version)
    assert promote_challenger_to_champion(
        client, "rivercast-kaub-6h", first_version, lambda _: True
    )

    second_logged, _ = _logged_run(config, fixture_dir, tmp_path, seed=7)
    second_version = register_candidate(client, "rivercast-kaub-6h", second_logged)
    assign_challenger(client, "rivercast-kaub-6h", second_version)

    promoted = promote_challenger_to_champion(
        client, "rivercast-kaub-6h", second_version, lambda _: False
    )

    assert not promoted
    champion = get_champion(client, "rivercast-kaub-6h")
    assert champion.version == first_version.version  # champion did not move
    fetched = client.get_model_version("rivercast-kaub-6h", second_version.version)
    assert fetched.tags["deployment_status"] == "failed"


def test_promote_challenger_to_champion_leaves_champion_unchanged_when_deploy_raises(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    assign_challenger(client, "rivercast-kaub-6h", model_version)

    def _raises(_: object) -> bool:
        raise RuntimeError("endpoint unreachable")

    promoted = promote_challenger_to_champion(client, "rivercast-kaub-6h", model_version, _raises)

    assert not promoted
    assert get_champion(client, "rivercast-kaub-6h") is None
    fetched = client.get_model_version("rivercast-kaub-6h", model_version.version)
    assert fetched.tags["deployment_status"] == "failed"


def test_promotion_is_idempotent(
    config, fixture_dir: Path, tmp_path: Path, client: MlflowClient
) -> None:
    logged, _ = _logged_run(config, fixture_dir, tmp_path)
    model_version = register_candidate(client, "rivercast-kaub-6h", logged)
    assign_challenger(client, "rivercast-kaub-6h", model_version)

    first = promote_challenger_to_champion(
        client, "rivercast-kaub-6h", model_version, lambda _: True
    )
    second = promote_challenger_to_champion(
        client, "rivercast-kaub-6h", model_version, lambda _: True
    )

    assert first and second
    champion = get_champion(client, "rivercast-kaub-6h")
    assert champion.version == model_version.version
