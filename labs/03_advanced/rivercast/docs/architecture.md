# RiverCast architecture (PLAN.md Phase 15)

This diagram reflects the implementation as it exists after Phase 14, not
the plan's original aspirational sketch — it is regenerated whenever the
pipeline DAGs, component set, or storage zones change materially (Phase 15
acceptance criterion: "the architecture diagram matches the
implementation"). Source of truth for each box: `docs/pipeline_components.md`
(components), `docs/adr/0002-data-versioning.md` (storage zones),
`pipelines/*.py` (DAG wiring).

## Component and data-flow diagram

```mermaid
flowchart TD
    subgraph ext["External"]
        PEGEL["PEGELONLINE REST API\n(live mode)"]
        FIXT["data_fixtures/pegelonline\n(fixture mode, default)"]
    end

    subgraph dataops["rivercast-data-ops pipeline (hourly)"]
        LOCK1["run_lock.acquire"]
        FETCH["fetch\n(one task per station)"]
        XFORM["transform\n(normalize -> resample -> features -> labels)"]
        VALIDATE["validate\n(quality + freshness gate)"]
        FORECAST["forecast\n(one task per horizon, dsl.If validate==ok)"]
        MONITOR["monitor\n(data_quality + drift + performance + retraining signal)"]
        DELAYED["delayed_metrics\n(join matured predictions)"]
        REL1["run_lock.release\n(dsl.ExitHandler, always runs)"]
    end

    subgraph modelpipe["rivercast-model pipeline (scheduled)"]
        LOCK2["run_lock.acquire"]
        TRIGGER["trigger\n(enough new rows? already trained?)"]
        TRAIN["train\n(persistence + candidate, dsl.If should_train)"]
        EVAL["evaluate\n(re-score on held-out test split)"]
        REGISTER["register\n(new MLflow model version)"]
        PROMOTE["promote\n(gates -> challenger -> deploy smoke test -> champion)"]
        REL2["run_lock.release\n(dsl.ExitHandler, always runs)"]
    end

    subgraph storage["Object store (local filesystem impl. / S3 interface)"]
        BRONZE["bronze/\nimmutable raw responses"]
        SILVER["silver/\nhourly canonical grid"]
        GOLD["gold/\nfeature tables + dataset manifests"]
        PRED["predictions/\nissued forecasts"]
        REPORTS["reports/\nquality, monitoring, evaluation"]
        LOCKS["locks/\nrun_lock markers"]
    end

    subgraph mlflow["MLflow"]
        TRACK["Tracking\n(runs, params, metrics, signature)"]
        REG["Model Registry\nrivercast-kaub-6h / -12h\naliases: challenger, champion"]
    end

    subgraph serving["Serving (FastAPI, KServe-compatible)"]
        API["/health /ready /metadata /predict\nloads champion per horizon from registry"]
    end

    PEGEL -.-> FETCH
    FIXT -.-> FETCH
    LOCK1 --> FETCH
    FETCH --> BRONZE
    BRONZE --> XFORM
    XFORM --> SILVER
    XFORM --> GOLD
    SILVER --> VALIDATE
    VALIDATE -- "status == ok" --> FORECAST
    REG -- "champion alias" --> FORECAST
    FORECAST --> PRED
    SILVER --> MONITOR
    PRED --> MONITOR
    MONITOR --> REPORTS
    SILVER --> DELAYED
    PRED --> DELAYED
    DELAYED --> REPORTS
    VALIDATE --> REL1
    MONITOR --> REL1
    DELAYED --> REL1
    LOCK1 -.-> LOCKS
    REL1 -.-> LOCKS

    LOCK2 --> TRIGGER
    GOLD --> TRIGGER
    TRACK -. "existing run for dataset_id?" .-> TRIGGER
    TRIGGER -- "should_train == True" --> TRAIN
    GOLD --> TRAIN
    TRAIN --> TRACK
    TRAIN --> EVAL
    EVAL --> REGISTER
    REGISTER --> REG
    REGISTER --> PROMOTE
    REG -- "current champion metrics" --> PROMOTE
    PROMOTE -- "smoke test passed" --> REG
    TRIGGER --> REL2
    PROMOTE --> REL2
    LOCK2 -.-> LOCKS
    REL2 -.-> LOCKS

    REG -- "champion, per horizon" --> API
```

## What each box is, and isn't, verified against

- Both pipelines compile to real KFP v2 YAML
  (`pipelines/compiled/rivercast-data-ops.yaml`,
  `pipelines/compiled/rivercast-model.yaml`) and are exercised end-to-end
  offline by `tests/integration/test_data_ops_pipeline.py` and
  `tests/integration/test_model_pipeline.py`. Real KFP `SubprocessRunner`
  execution on a live cluster and the OpenShift AI Pipelines UI are **not**
  verified in this environment (documented Windows/KFP incompatibility,
  Phase 8/9; re-verify in the Linux trainee workbench).
- The `run_lock` acquire/release boxes are new in Phase 15
  (`src/rivercast/concurrency.py`, `components/run_lock/`) — duplicate-run
  protection via an object-store-backed advisory lock, released through a
  KFP `ExitHandler` so a mid-pipeline failure still releases it.
- The object-store zones are exactly ADR 0002's six zones; `locks/` is a
  seventh, unzoned top-level prefix (not part of the bronze/silver/gold
  data-versioning contract, since lock markers are neither raw data nor a
  dataset).
- Serving is FastAPI today; the KServe `InferenceService`/`ServingRuntime`
  manifests under `deploy/` exist and validate (`kubectl kustomize`) but
  have not been applied to a live cluster from this environment (Phase 11
  gap, unchanged).
- `PEGEL`/`FIXT` are dashed because exactly one is active per `mode`
  (`fixture`/`live`) in config, never both.
