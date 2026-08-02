# ADR 0003 — Pipeline boundaries: two KFP pipelines, MLflow registry, KServe serving, scheduled continuous training

- **Status:** accepted
- **Date:** 2026-08-02
- **Deciders:** RiverCast maintainers
- **Related:** [ADR 0001](0001-rivercast-scope.md), [ADR 0002](0002-data-versioning.md), `PLAN.md` §3, Phases 8–12

## Context

The loop needs orchestration for hourly data operations and for periodic
retraining, plus experiment tracking, a model registry, and serving. Splitting
every concern into its own pipeline creates operational sprawl; merging data
operations and training into one pipeline couples an hourly cadence to a weekly
one and makes conditional retraining awkward.

## Decision

1. **Exactly two primary KFP v2 pipelines** on OpenShift AI Pipelines:
   - **`rivercast-data-ops`** (hourly): fetch → archive raw → normalize →
     validate → resample hourly → build latest features → invoke champion →
     store forecasts → join matured labels → delayed metrics → monitoring report.
   - **`rivercast-model`** (scheduled, initially weekly): check trigger → load
     dataset → validate → temporal split → train persistence + candidate →
     evaluate → compare champion → register challenger → conditional promotion →
     deploy → smoke test → rollback on failure.

   Separate concerns are separate Python components inside these pipelines, not
   separate pipelines.
2. **Continuous training is schedule + gate, not event-driven.** The model
   pipeline runs on a fixed schedule and exits early without training when there
   are too few new labeled rows, data quality fails, or the dataset ID was
   already trained. Monitoring writes a retraining-signal artifact that the
   pipeline reads, but all data and model gates still run. Drift alone never
   triggers retraining. No cross-pipeline event triggers, Kafka, or Airflow.
3. **MLflow is the tracker and registry.** Registered models
   `rivercast-kaub-6h` / `rivercast-kaub-12h` use aliases `challenger` and
   `champion`. Promotion is transactional: register → assign `challenger` →
   validate artifact → deploy to a non-production endpoint → smoke test → only
   then move `champion`, retaining the previous champion for rollback. A
   deployment failure must not move the `champion` alias. Fail closed: invalid
   data stops training and promotion.
4. **Serving is KServe-compatible.** Preferred order: an existing stable KServe
   runtime for the model format; else a custom `ServingRuntime` wrapping the
   FastAPI predictor; direct FastAPI-on-OpenShift remains a development fallback.
   No technology-preview runtime dependency. The serving layer reuses the
   training feature contract — it never re-implements feature code.
5. **Components are functions first.** Every pipeline step is an importable
   Python function under `src/rivercast/`, callable from JupyterLab and testable
   with KFP local execution, packaged into a small set of shared images
   (`rivercast-data`, `rivercast-train`, `rivercast-ops`, `rivercast-serving`)
   referenced by immutable tag or digest.

## Consequences

- Two schedules stay decoupled: data ops can run hourly and skip forecasting on
  stale sources without touching the training cadence.
- The registry is the single promotion control point; CI merging code never
  deploys a model by itself.
- Trainees see the same graph in the plan, the KFP UI, and the code — one
  pipeline per lifecycle, components as the unit of reuse.
- Event-driven retraining, canary rollout, and multi-station loops remain
  possible later without changing these boundaries (extension phases).
