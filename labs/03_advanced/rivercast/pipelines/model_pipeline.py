"""``rivercast-model`` KFP pipeline (PLAN.md Phase 10).

Wires the training/registry components into the plan's graph:

.. code-block:: text

    resolve-config
          |
          v
    check-training-trigger (components.trigger)
          |
          +-- should_train == False --> record skipped run (pipeline exits successfully)
          |
          v
    train-candidate (components.train; persistence is trained inside the
                      same component as the baseline comparison -- see
                      "train-persistence" note below)
          |
          v
    evaluate-and-slice (components.evaluate, re-scores the saved artifact)
          |
          v
    register (components.register)
          |
          v
    promote (components.promote -- evaluates gates against the *current*
             champion, then runs the real register->challenger->deploy->
             smoke-test->champion transaction from Phase 10 via
             components.deploy, never moving champion on a failed or
             rejected candidate)
```

``train-persistence`` is not a separate DAG node: ``components.train``
already fits the persistence baseline internally and compares the candidate
against it for the headline metrics (Phase 6 design, unchanged since) --
splitting it into its own KFP task would just be the same fit running a
second time for no additional information the pipeline needs. The
``apply-promotion-gates`` / ``rejected`` / ``approved`` branch, and the
``deploy candidate -> smoke test -> rollback|move champion`` sequence, both
live inside ``components.promote`` (Phase 7's ``promote_challenger_to_champion``
transaction, extended in Phase 10 to call the real ``components.deploy``
smoke test instead of an always-pass stub) rather than as separate KFP
tasks, because the transaction must run atomically: a separate "deploy"
task cannot inject its boolean result back into an in-progress "promote"
task's alias-move decision.

Every step is a thin ``@dsl.component`` wrapper around the matching
``components.<name>.component.run()`` — the authoritative logic stays in
``components/``, tested independently
(``tests/integration/test_model_pipeline.py``); this module is only the DAG
wiring and the trigger gate.

No ``from __future__ import annotations`` here (same as
``pipelines/data_ops_pipeline.py``): KFP's ``@dsl.component`` decorator
needs real type objects at decoration time, not PEP 563 postponed-string
annotations (see ``docs/pipeline_components.md``).
"""

from typing import NamedTuple

from kfp import compiler, dsl

_BASE_IMAGE = "python:3.12"
_PACKAGE = "rivercast"  # placeholder package spec; a pinned image replaces this per Phase 8/13


class TriggerOutputs(NamedTuple):
    status: str
    should_train: bool
    reason: str


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def trigger_task(
    config_path: str, lab_root: str, dataset_short_id: str, horizon_hours: int
) -> TriggerOutputs:
    """Decide whether to train for this dataset/horizon."""
    from pathlib import Path

    from components.trigger.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        dataset_short_id=dataset_short_id,
        horizon_hours=horizon_hours,
    )
    if result.status != "ok":
        return TriggerOutputs(
            status=result.status, should_train=False, reason=str(result.metadata.get("error", ""))
        )
    return TriggerOutputs(
        status=result.status,
        should_train=bool(result.metadata["should_train"]),
        reason=str(result.metadata.get("reason", "")),
    )


class TrainOutputs(NamedTuple):
    status: str
    mlflow_run_id: str
    model_path: str
    test_mae_cm: float
    test_skill_vs_persistence: float


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def train_task(
    config_path: str,
    lab_root: str,
    dataset_short_id: str,
    horizon_hours: int,
    model_name: str,
    seed: int,
) -> TrainOutputs:
    """Train one candidate (and the persistence baseline, internally) against the gold dataset."""
    from pathlib import Path

    from components.train.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        dataset_short_id=dataset_short_id,
        horizon_hours=horizon_hours,
        model_name=model_name,  # type: ignore[arg-type]
        seed=seed,
    )
    if result.status != "ok":
        return TrainOutputs(
            status=result.status,
            mlflow_run_id="",
            model_path="",
            test_mae_cm=0.0,
            test_skill_vs_persistence=0.0,
        )
    return TrainOutputs(
        status=result.status,
        mlflow_run_id=str(result.metadata["mlflow_run_id"]),
        model_path=str(result.metadata["model_path"]),
        test_mae_cm=float(result.metadata["test_mae_cm"]),
        test_skill_vs_persistence=float(result.metadata["test_skill_vs_persistence"]),
    )


class EvaluateOutputs(NamedTuple):
    status: str
    mae_cm: float
    rmse_cm: float
    skill_vs_persistence: float


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def evaluate_task(
    config_path: str,
    lab_root: str,
    dataset_short_id: str,
    horizon_hours: int,
    model_path: str,
    model_name: str,
) -> EvaluateOutputs:
    """Re-score the saved training artifact on the untouched test split."""
    from pathlib import Path

    from components.evaluate.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        dataset_short_id=dataset_short_id,
        horizon_hours=horizon_hours,
        model_path=Path(model_path),
        model_name=model_name,
        split_name="test",
    )
    if result.status != "ok":
        return EvaluateOutputs(
            status=result.status, mae_cm=0.0, rmse_cm=0.0, skill_vs_persistence=0.0
        )
    return EvaluateOutputs(
        status=result.status,
        mae_cm=float(result.metadata["mae_cm"]),
        rmse_cm=float(result.metadata["rmse_cm"]),
        skill_vs_persistence=float(result.metadata["skill_vs_persistence"]),
    )


class RegisterOutputs(NamedTuple):
    status: str
    registered_model_name: str
    model_version: str


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def register_task(
    config_path: str,
    lab_root: str,
    run_id: str,
    dataset_id: str,
    horizon_hours: int,
    model_name: str,
) -> RegisterOutputs:
    """Register the training run's model as a new candidate version."""
    from pathlib import Path

    from components.register.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        run_id=run_id,
        dataset_id=dataset_id,
        horizon_hours=horizon_hours,
        model_name=model_name,
    )
    if result.status != "ok":
        return RegisterOutputs(status=result.status, registered_model_name="", model_version="")
    return RegisterOutputs(
        status=result.status,
        registered_model_name=str(result.metadata["registered_model_name"]),
        model_version=str(result.metadata["model_version"]),
    )


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def promote_task(
    config_path: str,
    lab_root: str,
    registered_model_name: str,
    model_version: str,
    test_mae_cm: float,
    test_rmse_cm: float,
    test_persistence_mae_cm: float,
    test_skill_vs_persistence: float,
    dataset_short_id: str,
) -> str:
    """Evaluate promotion gates and, if they pass, run the real
    register->challenger->deploy->smoke-test->champion transaction.
    """
    import io
    from pathlib import Path

    import pandas as pd
    from components.promote.component import run

    from rivercast.config import load_config
    from rivercast.storage import create_object_store, zone_key

    config_p = Path(config_path)
    lab_root_p = Path(lab_root)
    config = load_config(config_p)
    storage_root = Path(config.storage.root)
    if not storage_root.is_absolute():
        storage_root = lab_root_p / storage_root
    store = create_object_store(config.storage.model_copy(update={"root": str(storage_root)}))

    prefix = zone_key(config.storage.zones, "gold", f"training/dataset_id={dataset_short_id}")
    dataset = pd.read_parquet(io.BytesIO(store.get_bytes(f"{prefix}/dataset.parquet")))
    feature_columns = [
        c for c in dataset.columns if not c.startswith("target_level_") and c != "issue_time_utc"
    ]
    latest_row = dataset.iloc[-1][feature_columns].fillna(0.0)
    smoke_test_features = {
        col: int(latest_row[col]) if col.startswith("missing_") else float(latest_row[col])
        for col in feature_columns
    }

    result = run(
        config_path=config_p,
        lab_root=lab_root_p,
        registered_model_name=registered_model_name,
        model_version=model_version,
        test_mae_cm=test_mae_cm,
        test_rmse_cm=test_rmse_cm,
        test_persistence_mae_cm=test_persistence_mae_cm,
        test_skill_vs_persistence=test_skill_vs_persistence,
        smoke_test_features=smoke_test_features,
    )
    return result.status


@dsl.pipeline(
    name="rivercast-model",
    description=(
        "Scheduled model pipeline: check the training trigger, train and "
        "evaluate a candidate against the current champion, and promote it "
        "only after a real deploy/smoke-test passes. Educational system; "
        "not a flood-warning product."
    ),
)
def rivercast_model_pipeline(
    config_path: str,
    lab_root: str,
    dataset_short_id: str,
    dataset_id: str,
    horizon_hours: int,
    model_name: str = "ridge",
    seed: int = 42,
    test_persistence_mae_cm: float = 0.0,
) -> None:
    """See the module docstring for the full graph. ``dataset_short_id``/
    ``dataset_id`` are resolved by the caller (the data-ops pipeline's
    ``transform`` step, or a notebook materializing one) rather than inside
    this pipeline, matching ``data_ops_pipeline.py``'s convention of passing
    resolved values through instead of hiding a config-file dependency
    inside the compiled YAML.
    """
    trigger = trigger_task(
        config_path=config_path,
        lab_root=lab_root,
        dataset_short_id=dataset_short_id,
        horizon_hours=horizon_hours,
    )

    with dsl.If(trigger.outputs["should_train"] == True):  # noqa: E712
        train = train_task(
            config_path=config_path,
            lab_root=lab_root,
            dataset_short_id=dataset_short_id,
            horizon_hours=horizon_hours,
            model_name=model_name,
            seed=seed,
        ).after(trigger)

        evaluate = evaluate_task(
            config_path=config_path,
            lab_root=lab_root,
            dataset_short_id=dataset_short_id,
            horizon_hours=horizon_hours,
            model_path=train.outputs["model_path"],
            model_name=model_name,
        ).after(train)

        register = register_task(
            config_path=config_path,
            lab_root=lab_root,
            run_id=train.outputs["mlflow_run_id"],
            dataset_id=dataset_id,
            horizon_hours=horizon_hours,
            model_name=model_name,
        ).after(evaluate)

        promote_task(
            config_path=config_path,
            lab_root=lab_root,
            registered_model_name=register.outputs["registered_model_name"],
            model_version=register.outputs["model_version"],
            test_mae_cm=evaluate.outputs["mae_cm"],
            test_rmse_cm=evaluate.outputs["rmse_cm"],
            test_persistence_mae_cm=test_persistence_mae_cm,
            test_skill_vs_persistence=evaluate.outputs["skill_vs_persistence"],
            dataset_short_id=dataset_short_id,
        ).after(register)


def compile_pipeline(output_path: str) -> None:
    compiler.Compiler().compile(rivercast_model_pipeline, output_path)


if __name__ == "__main__":
    compile_pipeline("pipelines/compiled/rivercast-model.yaml")
