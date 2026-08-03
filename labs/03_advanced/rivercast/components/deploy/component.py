"""Deploy component: validate a model version is loadable and smoke-test it
(PLAN.md Phase 8 component contract; real KServe deployment is Phase 11).

This is the honest, currently-implementable slice of "deploy": load the
model artifact by MLflow run/version exactly as serving would, run it
against a representative input, and check the prediction is finite. It does
**not** create a KServe ``InferenceService`` or any cluster resource yet —
that requires the serving layer (Phase 11) and the containerized runtime
image, neither of which exist. Rather than stub out a fake "deployed"
response, this component does the one piece of deployment validation that
*is* available now (artifact loadability + prediction sanity), and its
result is exactly what ``components.promote`` needs as its
``deploy_and_smoke_test`` callable once wired into a pipeline.

Container image: ``rivercast-serving`` (Containerfile.serving).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from mlflow.client import MlflowClient

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    model_run_uri,
    with_git_commit,
)
from rivercast.models.tracking import resolve_tracking_uri

_LOG = component_logger("deploy")


def run(
    config_path: Path,
    lab_root: Path,
    registered_model_name: str,
    model_version: str,
    smoke_test_features: dict[str, float],
) -> ComponentResult:
    """Load a registered model version and score one representative row.

    Fails closed: any load error or a non-finite prediction is a smoke-test
    failure (rule 13), never silently treated as success.
    """
    config = load_component_config(config_path)
    tracking_uri = resolve_tracking_uri(config, lab_root)
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    # Resolving the model version and loading/scoring it can each fail
    # independently (unknown version, corrupt artifact, schema mismatch);
    # all of it is smoke-test failure, never an unhandled exception
    # (rule 13: fail closed).
    model_uri = f"{registered_model_name}/{model_version}"
    try:
        model_uri = model_run_uri(client, registered_model_name, model_version)
        model = mlflow.pyfunc.load_model(model_uri)
        prediction = model.predict(pd.DataFrame([smoke_test_features]))
        # predict() may return a pandas Series or a bare numpy array
        # depending on the model flavor; normalize before indexing.
        value = float(np.asarray(prediction)[0])
    except Exception as exc:  # noqa: BLE001 -- any resolve/load/predict failure is a smoke-test failure
        _LOG.error("smoke test failed", extra={"model_uri": model_uri, "error": str(exc)})
        return ComponentResult(
            component="deploy",
            status="failed",
            metadata={"model_uri": model_uri, "error": str(exc)},
            code_commit=with_git_commit(lab_root),
        )

    if not math.isfinite(value):
        _LOG.error("smoke test failed: non-finite prediction", extra={"model_uri": model_uri})
        return ComponentResult(
            component="deploy",
            status="failed",
            metadata={"model_uri": model_uri, "prediction": value},
            code_commit=with_git_commit(lab_root),
        )

    _LOG.info("smoke test passed", extra={"model_uri": model_uri, "prediction": value})
    return ComponentResult(
        component="deploy",
        status="ok",
        metadata={"model_uri": model_uri, "prediction": value, "smoke_test_passed": True},
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Load and smoke-test a registered model version")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--registered-model-name", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--smoke-test-features-json", required=True)
    args = parser.parse_args(argv)

    result = run(
        config_path=args.config,
        lab_root=args.lab_root,
        registered_model_name=args.registered_model_name,
        model_version=args.model_version,
        smoke_test_features=json.loads(args.smoke_test_features_json),
    )
    emit(result)


if __name__ == "__main__":
    main()
