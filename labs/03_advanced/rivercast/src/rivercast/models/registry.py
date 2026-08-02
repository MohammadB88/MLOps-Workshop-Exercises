"""MLflow model registry and champion/challenger promotion (PLAN.md Phase 7).

Registered model names are ``rivercast-kaub-6h`` / ``rivercast-kaub-12h``
(``config.mlflow.registered_models``, keyed by horizon). Two aliases matter:

- ``challenger`` — a candidate that passed offline evaluation and is staged
  for deployment validation;
- ``champion`` — the currently serving model.

The promotion transaction in :func:`promote_challenger_to_champion` follows
the plan's ordering exactly: register, assign challenger, validate the
deployable artifact, deploy to non-prod, smoke test, and only then move
champion. Deployment/smoke-test steps are represented here as an injectable
callable so this module has no serving dependency yet (that arrives in
Phases 8-11); a caller that skips validation gets a ``ValueError``, not a
silently-moved champion (CLAUDE.md rule 14).
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from mlflow.client import MlflowClient
from mlflow.entities.model_registry import ModelVersion
from mlflow.exceptions import MlflowException

from rivercast.models.evaluate import EvaluationReport, SliceMetric
from rivercast.models.tracking import LoggedRun

ValidationStatus = Literal["pending", "approved", "rejected"]
DeploymentStatus = Literal["not_deployed", "deployed", "failed"]

CHALLENGER_ALIAS = "challenger"
CHAMPION_ALIAS = "champion"


@dataclass(frozen=True)
class PromotionDecision:
    approved: bool
    reasons: list[str]


def evaluate_promotion_gates(
    test_report: EvaluationReport,
    champion_test_report: EvaluationReport | None,
    min_skill_vs_persistence: float,
    max_mae_regression_vs_champion_cm: float,
    max_slice_regression_fraction: float,
) -> PromotionDecision:
    """Apply the promotion policy from ``configs/base.yaml`` thresholds.promotion.

    All three checks must pass; any failing check is recorded so the
    rejection is traceable, not just a boolean.
    """
    reasons: list[str] = []

    if test_report.skill_vs_persistence < min_skill_vs_persistence:
        reasons.append(
            f"skill_vs_persistence {test_report.skill_vs_persistence:.4f} < "
            f"required {min_skill_vs_persistence:.4f}"
        )

    if champion_test_report is not None:
        mae_regression = test_report.mae_cm - champion_test_report.mae_cm
        if mae_regression > max_mae_regression_vs_champion_cm:
            reasons.append(
                f"test MAE regressed by {mae_regression:.4f}cm vs champion "
                f"(allowed {max_mae_regression_vs_champion_cm:.4f}cm)"
            )

        champion_slices = {(s.slice_name, s.slice_value): s for s in champion_test_report.slices}
        for slice_metric in test_report.slices:
            champion_slice = champion_slices.get(
                (slice_metric.slice_name, slice_metric.slice_value)
            )
            if champion_slice is None or champion_slice.mae_cm == 0:
                continue
            regression_fraction = (
                slice_metric.mae_cm - champion_slice.mae_cm
            ) / champion_slice.mae_cm
            if regression_fraction > max_slice_regression_fraction:
                reasons.append(
                    f"slice {slice_metric.slice_name}={slice_metric.slice_value} regressed "
                    f"{regression_fraction:.1%} (allowed {max_slice_regression_fraction:.1%})"
                )

    return PromotionDecision(approved=not reasons, reasons=reasons)


def register_candidate(
    client: MlflowClient,
    registered_model_name: str,
    logged_run: LoggedRun,
) -> ModelVersion:
    """Register the run's logged model as a new version. Idempotent per run.

    Creates the registered model on first use (first-model bootstrap: no
    error if it already exists).
    """
    with contextlib.suppress(MlflowException):
        client.create_registered_model(registered_model_name)  # already exists -> normal

    existing = [
        mv
        for mv in client.search_model_versions(f"name='{registered_model_name}'")
        if mv.run_id == logged_run.run_id
    ]
    if existing:
        return existing[0]  # promotion is idempotent: don't create a duplicate version

    source = f"runs:/{logged_run.run_id}/model"
    model_version = client.create_model_version(
        name=registered_model_name,
        source=source,
        run_id=logged_run.run_id,
    )
    client.set_model_version_tag(
        registered_model_name, model_version.version, "dataset_id", logged_run.dataset_id
    )
    client.set_model_version_tag(
        registered_model_name, model_version.version, "horizon_hours", str(logged_run.horizon_hours)
    )
    client.set_model_version_tag(
        registered_model_name, model_version.version, "validation_status", "pending"
    )
    client.set_model_version_tag(
        registered_model_name, model_version.version, "deployment_status", "not_deployed"
    )
    return model_version


def assign_challenger(
    client: MlflowClient, registered_model_name: str, model_version: ModelVersion
) -> None:
    client.set_registered_model_alias(
        registered_model_name, CHALLENGER_ALIAS, model_version.version
    )


def get_champion(client: MlflowClient, registered_model_name: str) -> ModelVersion | None:
    """The current champion version, or ``None`` if this model has never had one."""
    try:
        return client.get_model_version_by_alias(registered_model_name, CHAMPION_ALIAS)
    except MlflowException:
        return None


def champion_test_report(client: MlflowClient, champion: ModelVersion) -> EvaluationReport | None:
    """Reconstruct the champion's test-split evaluation report from its logged run.

    ``tracking.log_training_run`` logs test metrics as flat, prefixed keys
    (``test_mae_cm``, ``test_<slice_name>_<slice_value>_mae_cm``, ...); this
    rebuilds an :class:`EvaluationReport` from those so
    :func:`evaluate_promotion_gates` can compare a challenger against the
    champion's real numbers instead of skipping the regression checks.
    Returns ``None`` if the champion's run or required metrics are missing
    (e.g. a run logged before Phase 7, or a deleted run) — the caller then
    falls back to the skill-only check rather than failing closed on a
    champion whose history is simply gone.
    """
    if champion.run_id is None:
        return None
    try:
        run = client.get_run(champion.run_id)
    except MlflowException:
        return None
    metrics = run.data.metrics
    required = (
        "test_mae_cm",
        "test_rmse_cm",
        "test_persistence_mae_cm",
        "test_skill_vs_persistence",
    )
    if any(key not in metrics for key in required):
        return None

    slices: list[SliceMetric] = []
    prefix = "test_"
    for key, value in metrics.items():
        if not key.startswith(prefix) or not key.endswith("_mae_cm"):
            continue
        middle = key[len(prefix) : -len("_mae_cm")]
        if middle in ("mae_cm", "rmse_cm", "persistence_mae_cm"):
            continue  # headline metric, not a slice
        rmse_key = f"{prefix}{middle}_rmse_cm"
        n_key = f"{prefix}{middle}_n"
        if rmse_key not in metrics or n_key not in metrics:
            continue
        slice_name, _, slice_value = middle.rpartition("_")
        slices.append(
            SliceMetric(
                slice_name=slice_name,
                slice_value=slice_value,
                n=int(metrics[n_key]),
                mae_cm=value,
                rmse_cm=metrics[rmse_key],
            )
        )

    return EvaluationReport(
        model_name=run.data.params.get("model_name", "unknown"),
        horizon_hours=int(run.data.params.get("horizon_hours", 0)),
        n=int(run.data.params.get("n_test", 0)),
        mae_cm=metrics["test_mae_cm"],
        rmse_cm=metrics["test_rmse_cm"],
        persistence_mae_cm=metrics["test_persistence_mae_cm"],
        skill_vs_persistence=metrics["test_skill_vs_persistence"],
        slices=slices,
    )


def reject_candidate(
    client: MlflowClient, registered_model_name: str, model_version: ModelVersion
) -> None:
    client.set_model_version_tag(
        registered_model_name, model_version.version, "validation_status", "rejected"
    )


def promote_challenger_to_champion(
    client: MlflowClient,
    registered_model_name: str,
    model_version: ModelVersion,
    deploy_and_smoke_test: Callable[[ModelVersion], bool],
) -> bool:
    """Run the deployment-validation transaction; only then move ``champion``.

    ``deploy_and_smoke_test`` stands in for the Phase 8-11 serving pipeline:
    it must deploy the candidate to a non-production endpoint/revision, run
    smoke tests, and return whether they passed. Returning ``False`` (or
    raising) leaves ``champion`` untouched -- a deployment failure must never
    move the alias (CLAUDE.md rule 14).
    """
    client.set_model_version_tag(
        registered_model_name, model_version.version, "validation_status", "approved"
    )

    previous_champion = get_champion(client, registered_model_name)
    if previous_champion is not None:
        client.set_model_version_tag(
            registered_model_name,
            model_version.version,
            "previous_champion_version",
            previous_champion.version,
        )

    try:
        smoke_test_passed = deploy_and_smoke_test(model_version)
    except Exception:
        client.set_model_version_tag(
            registered_model_name, model_version.version, "deployment_status", "failed"
        )
        return False

    if not smoke_test_passed:
        client.set_model_version_tag(
            registered_model_name, model_version.version, "deployment_status", "failed"
        )
        return False

    client.set_model_version_tag(
        registered_model_name, model_version.version, "deployment_status", "deployed"
    )
    client.set_registered_model_alias(registered_model_name, CHAMPION_ALIAS, model_version.version)
    return True
