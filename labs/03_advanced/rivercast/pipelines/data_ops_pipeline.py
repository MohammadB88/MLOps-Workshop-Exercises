"""``rivercast-data-ops`` KFP pipeline (PLAN.md Phase 9).

Wires the Phase 8 components into the pipeline graph from the plan:

.. code-block:: text

    resolve-config
          |
          v
    fetch-live-measurements (one task per configured station, ParallelFor)
          |
          v
    archive-and-normalize / validate-and-resample-hourly
    (components.transform builds bronze->silver->gold in one step; Phase 8
     note: normalize/resample/features/labels share one input and gain
     nothing from separate container steps at this lab's scale)
          |
          v
    validate-and-resample-hourly (components.validate: quality + freshness gate)
          |
          +-------------------------------+
          v                               v
    dsl.If(validate passed)          join-matured-predictions +
    issue-6h/12h forecasts           calculate-delayed-metrics
    (components.forecast, one       (components... via
     task per configured horizon)    join_matured_predictions/
          |                          calculate_delayed_metrics)
          v                               v
          +------------> monitoring-report (components.monitor) <---+

A stale or otherwise-failed validation skips forecasting entirely (PLAN.md
Phase 9 schedule: "if source data is not fresh enough: do not issue a
forecast ... keep the last deployed model unchanged") via a real
``dsl.If`` branch on ``validate_task``'s typed ``status`` output — not a
placeholder condition. ``monitor`` and the delayed-metrics step still run
on a failed validation, since they report on the data itself regardless of
whether it was fresh enough to forecast from.

Every step is a thin ``@dsl.component`` wrapper that imports and calls the
matching ``components.<name>.component.run()`` (or, for the join step, the
``rivercast.processing.delayed_metrics`` functions directly) — the
authoritative logic stays in ``components/``/``src/rivercast/``, tested
independently; this module is only the DAG wiring plus the typed outputs
KFP needs to branch on.

Caching is disabled on every live-fetch, forecast, label-join, and
monitoring step (plan §Phase 9 schedule) since their inputs are the
mutable, time-varying "now"; the deterministic ``transform`` step keeps
KFP's default caching.
"""

# No `from __future__ import annotations` here: KFP's @dsl.component decorator
# inspects parameter/return type annotations at decoration time and requires
# real type objects, not PEP 563 postponed-evaluation strings -- with
# postponed annotations every parameter type resolves to the literal string
# "str"/"int" instead of the type itself, and KFP's artifact-type validator
# misreads that string as a malformed bundled-artifact type
# ("Artifacts must have both a schema_title and a schema_version").
# Reproduces even for a trivial `def add(a: int, b: int) -> int` component.
from typing import NamedTuple

from kfp import compiler, dsl

_BASE_IMAGE = "python:3.12"
_PACKAGE = "rivercast"  # placeholder package spec; a pinned image replaces this per Phase 8/13


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def fetch_station_task(
    config_path: str,
    lab_root: str,
    station_uuid: str,
    parameter: str,
    start: str,
    end: str,
    fixture_dir: str,
) -> str:
    """One ``components.fetch`` call for one station; returns its status."""
    from datetime import UTC, datetime
    from pathlib import Path

    from components.fetch.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        station_uuid=station_uuid,
        parameter=parameter,
        start=datetime.fromisoformat(start).astimezone(UTC),
        end=datetime.fromisoformat(end).astimezone(UTC),
        fixture_dir=Path(fixture_dir) if fixture_dir else None,
    )
    return result.status


class TransformOutputs(NamedTuple):
    status: str
    dataset_short_id: str
    silver_key: str


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def transform_task(config_path: str, lab_root: str, start: str, end: str) -> TransformOutputs:
    """Bronze -> silver hourly grid -> gold training dataset."""
    from datetime import UTC, datetime
    from pathlib import Path

    from components.transform.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        start=datetime.fromisoformat(start).astimezone(UTC),
        end=datetime.fromisoformat(end).astimezone(UTC),
    )
    if result.status != "ok":
        return TransformOutputs(status=result.status, dataset_short_id="", silver_key="")

    dataset_id = str(result.metadata["dataset_id"])
    silver_key = next(k for k in result.output_keys if k.startswith("silver/"))
    return TransformOutputs(
        status=result.status,
        dataset_short_id=dataset_id.removeprefix("sha256:")[:12],
        silver_key=silver_key,
    )


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def validate_task(config_path: str, lab_root: str, silver_key: str, now_utc: str) -> str:
    """Quality gate + freshness check over the silver hourly window; returns status."""
    from datetime import datetime
    from pathlib import Path

    from components.validate.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        silver_key=silver_key,
        now_utc=datetime.fromisoformat(now_utc),
    )
    return result.status


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def monitor_task(config_path: str, lab_root: str, silver_key: str, now_utc: str) -> str:
    """Freshness/coverage summary, independent of whether validation passed."""
    from datetime import datetime
    from pathlib import Path

    from components.monitor.component import run

    result = run(
        config_path=Path(config_path),
        lab_root=Path(lab_root),
        silver_key=silver_key,
        now_utc=datetime.fromisoformat(now_utc),
    )
    return result.status


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def forecast_task(
    config_path: str,
    lab_root: str,
    horizon_hours: int,
    issue_time: str,
    dataset_short_id: str,
    pipeline_run_id: str,
) -> str:
    """Load the champion for one horizon and issue+persist one prediction
    from the latest feature row in the just-built gold dataset.
    """
    import io
    from datetime import UTC, datetime
    from pathlib import Path

    import pandas as pd
    from components.forecast.component import run

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
    features = {col: float(latest_row[col]) for col in feature_columns}

    result = run(
        config_path=config_p,
        lab_root=lab_root_p,
        horizon_hours=horizon_hours,
        issue_time=datetime.fromisoformat(issue_time).astimezone(UTC),
        features=features,
        created_by_pipeline_run=pipeline_run_id,
    )
    return result.status


@dsl.component(base_image=_BASE_IMAGE, packages_to_install=[_PACKAGE])
def delayed_metrics_task(
    config_path: str, lab_root: str, silver_key: str, horizons_hours: list[int], now_utc: str
) -> str:
    """Join every persisted prediction against the silver hourly grid and
    compute delayed MAE/RMSE per horizon; writes one report to
    ``reports/delayed_metrics/``.
    """
    from datetime import datetime
    from pathlib import Path

    from components.common import open_store, read_json, write_json

    from rivercast.config import load_config
    from rivercast.contracts.hourly import HourlyObservation
    from rivercast.contracts.predictions import PredictionRecord
    from rivercast.processing.delayed_metrics import (
        calculate_delayed_metrics,
        join_matured_predictions,
    )
    from rivercast.storage import zone_key

    config_p = Path(config_path)
    lab_root_p = Path(lab_root)
    config = load_config(config_p)
    store = open_store(config, lab_root_p)
    now = datetime.fromisoformat(now_utc)

    hourly_rows = read_json(store, silver_key)
    hourly = [HourlyObservation.model_validate(row) for row in hourly_rows]

    predictions: list[PredictionRecord] = []
    for horizon in horizons_hours:
        prefix = zone_key(config.storage.zones, "predictions", f"horizon_hours={horizon}")
        for key in store.list_keys(f"{prefix}/"):
            predictions.append(PredictionRecord.model_validate(read_json(store, key)))

    matured = join_matured_predictions(predictions, hourly, now_utc=now)
    metrics = [calculate_delayed_metrics(matured, horizon) for horizon in horizons_hours]

    report = {
        "checked_at_utc": now.isoformat(timespec="seconds"),
        "metrics": [
            {
                "horizon_hours": m.horizon_hours,
                "n_matured": m.n_matured,
                "n_total": m.n_total,
                "mae_cm": m.mae_cm,
                "rmse_cm": m.rmse_cm,
            }
            for m in metrics
        ],
    }
    report_key = zone_key(
        config.storage.zones,
        "reports",
        "delayed_metrics",
        f"{silver_key.rsplit('/', 1)[-1].removesuffix('.json')}_delayed_metrics.json",
    )
    write_json(store, report_key, report, overwrite=True)
    return "ok"


@dsl.pipeline(
    name="rivercast-data-ops",
    description=(
        "Hourly data-operations pipeline: fetch, archive, validate, issue "
        "forecasts from the champion model, and calculate delayed accuracy "
        "once predictions mature. Educational system; not a flood-warning "
        "product."
    ),
)
def rivercast_data_ops_pipeline(
    config_path: str,
    lab_root: str,
    station_uuids: list[str],
    parameter: str,
    window_start: str,
    window_end: str,
    horizons_hours: list[int],
    fixture_dir: str = "",
    pipeline_run_id: str = "",
) -> None:
    """See the module docstring for the full graph. ``window_start``/
    ``window_end``/``station_uuids``/``horizons_hours`` are passed explicitly
    (not read from config inside the pipeline definition) so the compiled
    YAML has no hidden config-file dependency at submission time — the
    caller (CLI or a KFP recurring run) resolves them from ``configs/*.yaml``
    once and passes the resolved values through.
    """
    fetch_tasks = []
    with dsl.ParallelFor(station_uuids, parallelism=4) as station_uuid:
        fetch_task = fetch_station_task(
            config_path=config_path,
            lab_root=lab_root,
            station_uuid=station_uuid,
            parameter=parameter,
            start=window_start,
            end=window_end,
            fixture_dir=fixture_dir,
        )
        fetch_task.set_caching_options(enable_caching=False)
        fetch_tasks.append(fetch_task)

    transform = transform_task(
        config_path=config_path, lab_root=lab_root, start=window_start, end=window_end
    ).after(*fetch_tasks)
    # Deterministic given its bronze inputs -- default caching stays enabled.

    validate = validate_task(
        config_path=config_path,
        lab_root=lab_root,
        silver_key=transform.outputs["silver_key"],
        now_utc=window_end,
    ).after(transform)
    validate.set_caching_options(enable_caching=False)

    monitor = monitor_task(
        config_path=config_path,
        lab_root=lab_root,
        silver_key=transform.outputs["silver_key"],
        now_utc=window_end,
    ).after(transform)
    monitor.set_caching_options(enable_caching=False)

    # Real freshness/quality gate: forecasting only runs when validate_task
    # actually reported "ok" (PLAN.md Phase 9 schedule -- a stale or invalid
    # window must not issue a forecast). forecast_task itself still fails
    # closed independently (no champion, bad horizon) if ever called
    # directly outside this gate. horizons_hours is a pipeline-parameter
    # channel, not a plain Python list, at compile time -- iterate it with
    # dsl.ParallelFor, the same as station_uuids above, rather than a bare
    # `for` loop (which raises "PipelineParameterChannel object is not
    # iterable").
    # Kept as nested `with` blocks (not combined into one `with` statement):
    # dsl.If / dsl.ParallelFor are KFP DAG-scoping context managers, not
    # ordinary ones, and combining them changes which tasks group under
    # which control-flow node.
    with dsl.If(validate.output == "ok"):  # noqa: SIM117
        with dsl.ParallelFor(horizons_hours, parallelism=2) as horizon:
            forecast = forecast_task(
                config_path=config_path,
                lab_root=lab_root,
                horizon_hours=horizon,
                issue_time=window_end,
                dataset_short_id=transform.outputs["dataset_short_id"],
                pipeline_run_id=pipeline_run_id,
            ).after(validate)
            forecast.set_caching_options(enable_caching=False)

    delayed_metrics = delayed_metrics_task(
        config_path=config_path,
        lab_root=lab_root,
        silver_key=transform.outputs["silver_key"],
        horizons_hours=horizons_hours,
        now_utc=window_end,
    ).after(transform)
    delayed_metrics.set_caching_options(enable_caching=False)


def compile_pipeline(output_path: str) -> None:
    compiler.Compiler().compile(rivercast_data_ops_pipeline, output_path)


if __name__ == "__main__":
    compile_pipeline("pipelines/compiled/rivercast-data-ops.yaml")
