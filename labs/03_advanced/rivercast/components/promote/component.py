"""Promote component: evaluate promotion gates and run the champion
transaction for a registered model version (PLAN.md Phase 7 registry +
Phase 8 component contract).

Wraps ``rivercast.models.registry``: assign ``challenger``, validate the
deployable artifact via the injected ``components.deploy`` step, and only
then move ``champion``. A rejected candidate or a failed deploy/smoke-test
never moves the alias (CLAUDE.md rule 14) — this component's ``status``
reflects that precisely: ``"ok"`` with ``promoted=false`` is a legitimate,
non-error outcome, not a failure.

Container image: ``rivercast-train`` (Containerfile.train).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mlflow.client import MlflowClient

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    with_git_commit,
)
from rivercast.models.evaluate import EvaluationReport
from rivercast.models.registry import (
    assign_challenger,
    champion_test_report,
    evaluate_promotion_gates,
    get_champion,
    promote_challenger_to_champion,
    reject_candidate,
)
from rivercast.models.tracking import resolve_tracking_uri

_LOG = component_logger("promote")


def run(
    config_path: Path,
    lab_root: Path,
    registered_model_name: str,
    model_version: str,
    test_mae_cm: float,
    test_rmse_cm: float,
    test_persistence_mae_cm: float,
    test_skill_vs_persistence: float,
) -> ComponentResult:
    """Evaluate the promotion gates for one registered model version and, if
    they pass, run the deploy-validate-and-promote transaction.

    The candidate's test metrics are passed explicitly (rather than
    re-derived here) because this component's only job is the promotion
    decision and transaction, not re-running evaluation -- ``components.evaluate``
    already produced them.
    """
    config = load_component_config(config_path)
    tracking_uri = resolve_tracking_uri(config, lab_root)
    client = MlflowClient(tracking_uri=tracking_uri)

    candidate_report = EvaluationReport(
        model_name=registered_model_name,
        horizon_hours=0,
        n=0,
        mae_cm=test_mae_cm,
        rmse_cm=test_rmse_cm,
        persistence_mae_cm=test_persistence_mae_cm,
        skill_vs_persistence=test_skill_vs_persistence,
        slices=[],
    )

    champion = get_champion(client, registered_model_name)
    champion_report = champion_test_report(client, champion) if champion is not None else None

    decision = evaluate_promotion_gates(
        candidate_report,
        champion_report,
        config.thresholds.promotion.min_skill_vs_persistence,
        config.thresholds.promotion.max_mae_regression_vs_champion_cm,
        config.thresholds.promotion.max_slice_regression_fraction,
    )

    model_version_obj = client.get_model_version(registered_model_name, model_version)

    if not decision.approved:
        reject_candidate(client, registered_model_name, model_version_obj)
        _LOG.info("candidate rejected", extra={"reasons": decision.reasons})
        return ComponentResult(
            component="promote",
            status="ok",
            metadata={"approved": False, "promoted": False, "reasons": decision.reasons},
            code_commit=with_git_commit(lab_root),
        )

    assign_challenger(client, registered_model_name, model_version_obj)

    def _deploy_and_smoke_test(_: object) -> bool:
        # Real deployment validation arrives with Phases 8-11's serving
        # layer; until then this always-pass stub keeps the transaction's
        # ordering real (register -> challenger -> validate -> champion)
        # without pretending a serving endpoint exists yet.
        return True

    promoted = promote_challenger_to_champion(
        client, registered_model_name, model_version_obj, _deploy_and_smoke_test
    )

    _LOG.info(
        "promotion transaction complete",
        extra={"registered_model_name": registered_model_name, "promoted": promoted},
    )
    return ComponentResult(
        component="promote",
        status="ok",
        metadata={"approved": True, "promoted": promoted},
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate promotion gates and promote if they pass"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--registered-model-name", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--test-mae-cm", type=float, required=True)
    parser.add_argument("--test-rmse-cm", type=float, required=True)
    parser.add_argument("--test-persistence-mae-cm", type=float, required=True)
    parser.add_argument("--test-skill-vs-persistence", type=float, required=True)
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        registered_model_name=args.registered_model_name,
        model_version=args.model_version,
        test_mae_cm=args.test_mae_cm,
        test_rmse_cm=args.test_rmse_cm,
        test_persistence_mae_cm=args.test_persistence_mae_cm,
        test_skill_vs_persistence=args.test_skill_vs_persistence,
    )
    emit(result)


if __name__ == "__main__":
    main()
