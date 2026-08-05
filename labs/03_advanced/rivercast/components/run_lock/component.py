"""Run-lock component: duplicate-run protection for scheduled pipelines
(PLAN.md Phase 15 "duplicate-run protection" / "pipeline concurrency policy").

Two subcommands, both thin wrappers around
:class:`rivercast.concurrency.PipelineRunLock`:

- ``acquire`` -- the first task in a pipeline DAG; fails closed
  (``status="failed"``, non-zero exit) if another run of the same pipeline
  name is still holding the lock, so KFP fails the whole run before any
  work starts rather than letting two runs race on the same object-store
  keys and MLflow aliases.
- ``release`` -- the last task; always attempts to run even if earlier
  tasks failed (a KFP ``exit_task``/``.after()`` on every branch), since a
  lock that outlives its run would wedge every future scheduled tick.

Container image: ``rivercast-ops`` (Containerfile.ops).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from components.common import (
    ComponentResult,
    component_logger,
    emit,
    load_component_config,
    open_store,
    with_git_commit,
)
from rivercast.concurrency import PipelineAlreadyRunningError, PipelineRunLock

_LOG = component_logger("run_lock")


def acquire(config_path: Path, lab_root: Path, pipeline_name: str, run_id: str) -> ComponentResult:
    config = load_component_config(config_path)
    store = open_store(config, lab_root)
    lock = PipelineRunLock(store)
    try:
        info = lock.acquire(pipeline_name, run_id)
    except PipelineAlreadyRunningError as exc:
        _LOG.error("run lock refused", extra={"pipeline_name": pipeline_name, "error": str(exc)})
        return ComponentResult(
            component="run_lock.acquire",
            status="failed",
            metadata={"pipeline_name": pipeline_name, "error": str(exc)},
            code_commit=with_git_commit(lab_root),
        )
    _LOG.info("run lock acquired", extra={"pipeline_name": pipeline_name, "run_id": run_id})
    return ComponentResult(
        component="run_lock.acquire",
        status="ok",
        metadata={
            "pipeline_name": pipeline_name,
            "run_id": run_id,
            "acquired_at_utc": info.acquired_at_utc,
        },
        code_commit=with_git_commit(lab_root),
    )


def release(config_path: Path, lab_root: Path, pipeline_name: str, run_id: str) -> ComponentResult:
    config = load_component_config(config_path)
    store = open_store(config, lab_root)
    lock = PipelineRunLock(store)
    lock.release(pipeline_name, run_id)
    _LOG.info("run lock released", extra={"pipeline_name": pipeline_name, "run_id": run_id})
    return ComponentResult(
        component="run_lock.release",
        status="ok",
        metadata={"pipeline_name": pipeline_name, "run_id": run_id},
        code_commit=with_git_commit(lab_root),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Acquire or release the duplicate-run lock for a pipeline"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--pipeline-name", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--action", required=True, choices=["acquire", "release"])
    args = parser.parse_args(argv)

    if args.action == "acquire":
        result = acquire(args.config, args.lab_root, args.pipeline_name, args.run_id)
    else:
        result = release(args.config, args.lab_root, args.pipeline_name, args.run_id)
    emit(result)


if __name__ == "__main__":
    main()
