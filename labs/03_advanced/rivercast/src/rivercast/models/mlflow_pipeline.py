"""End-to-end train -> track -> register -> (optionally) promote (Phase 7).

Composes ``local_pipeline.run_training``, ``tracking.log_training_run``, and
``registry`` into the single workflow the CLI and
``04_mlflow_tracking.ipynb`` call. Promotion only runs when the caller opts
in (``promote=True``); logging and registration always happen so every run
is traceable even when it is not a promotion candidate.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mlflow.client import MlflowClient
from mlflow.entities.model_registry import ModelVersion

from rivercast.config import RivercastConfig
from rivercast.models.local_pipeline import TrainRunResult, run_training
from rivercast.models.registry import (
    PromotionDecision,
    assign_challenger,
    champion_test_report,
    evaluate_promotion_gates,
    get_champion,
    promote_challenger_to_champion,
    register_candidate,
    reject_candidate,
)
from rivercast.models.tracking import LoggedRun, log_training_run, resolve_tracking_uri
from rivercast.models.train import ModelName


@dataclass(frozen=True)
class TrackedTrainingOutcome:
    train_result: TrainRunResult
    logged_run: LoggedRun
    registered_model_name: str
    model_version: ModelVersion
    decision: PromotionDecision
    champion_model_version: str | None
    promoted: bool


def _always_pass_smoke_test(_: ModelVersion) -> bool:
    """Default deploy/smoke-test stand-in until Phases 8-11 add real serving."""
    return True


def train_track_and_register(
    config: RivercastConfig,
    lab_root: Path,
    fixture_dir: Path,
    horizon_hours: int,
    model_name: ModelName,
    models_dir: Path,
    seed: int = 42,
    promote: bool = False,
    deploy_and_smoke_test: Callable[[ModelVersion], bool] = _always_pass_smoke_test,
) -> TrackedTrainingOutcome:
    """Train, log to MLflow, register a candidate version, and evaluate gates.

    Always registers the candidate (traceable, per acceptance criteria) even
    when the promotion gates reject it or ``promote`` is left ``False`` — a
    rejected candidate must remain visible in the registry, just without the
    ``champion`` alias (PLAN.md Phase 7 acceptance criteria).
    """
    train_result = run_training(
        config, fixture_dir, horizon_hours, model_name, models_dir, seed=seed
    )
    logged_run = log_training_run(config, lab_root, train_result)

    tracking_uri = resolve_tracking_uri(config, lab_root)
    client = MlflowClient(tracking_uri=tracking_uri)

    registered_model_name = config.mlflow.registered_models[str(horizon_hours)]
    model_version = register_candidate(client, registered_model_name, logged_run)

    champion = get_champion(client, registered_model_name)
    # First-model bootstrap: no champion yet (or its metrics are unavailable)
    # means no regression comparison is possible, so the decision falls back
    # to the skill-only check.
    champion_report = champion_test_report(client, champion) if champion is not None else None

    decision = evaluate_promotion_gates(
        train_result.test_report,
        champion_report,
        config.thresholds.promotion.min_skill_vs_persistence,
        config.thresholds.promotion.max_mae_regression_vs_champion_cm,
        config.thresholds.promotion.max_slice_regression_fraction,
    )

    promoted = False
    if not decision.approved:
        reject_candidate(client, registered_model_name, model_version)
    elif promote:
        assign_challenger(client, registered_model_name, model_version)
        promoted = promote_challenger_to_champion(
            client, registered_model_name, model_version, deploy_and_smoke_test
        )
    else:
        client.set_model_version_tag(
            registered_model_name, model_version.version, "validation_status", "approved"
        )

    return TrackedTrainingOutcome(
        train_result=train_result,
        logged_run=logged_run,
        registered_model_name=registered_model_name,
        model_version=model_version,
        decision=decision,
        champion_model_version=champion.version if champion else None,
        promoted=promoted,
    )
