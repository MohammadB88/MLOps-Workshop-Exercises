# RiverCast — Level-1 Continuous Forecasting Capstone

> **Educational system — not a flood-warning product.** RiverCast exists to
> teach MLOps. Its forecasts must never be used for navigation, flood
> protection, or any real-world decision. PEGELONLINE water level is measured
> relative to the local gauge zero — it is **not** the river depth.

RiverCast is the advanced capstone lab of the MLOps workshop: a Level-1
automated ML system that continuously collects river-gauge data from
[PEGELONLINE](https://www.pegelonline.wsv.de/), forecasts the water level at
**KAUB on the Rhine** 6 and 12 hours ahead, evaluates each forecast once the
actual measurement arrives, retrains on a schedule, and promotes only
validated candidates to a KServe-compatible endpoint on OpenShift AI.

## What it teaches

- time-series pipelines without data leakage or timestamp/DST errors;
- immutable raw data, versioned datasets, and full lineage (dataset → model);
- champion/challenger promotion with mandatory validation gates;
- monitoring with delayed ground truth and conditional scheduled retraining;
- fixture-first development: the whole lab runs without internet access.

## Status

**In development.** Phases, acceptance criteria, and deliverables are defined
in [PLAN.md](PLAN.md); current phase status is tracked in
[PROGRESS.md](PROGRESS.md). Key decisions are recorded as ADRs under
[docs/adr/](docs/adr/):

| ADR | Decision |
|---|---|
| [0001](docs/adr/0001-rivercast-scope.md) | Gauge-only MVP: KAUB, 6 h / 12 h horizons, hourly grid, explicit non-goals |
| [0002](docs/adr/0002-data-versioning.md) | Immutable bronze/silver/gold storage, dataset manifests, fixture mode by default |
| [0003](docs/adr/0003-pipeline-boundaries.md) | Two KFP pipelines, MLflow registry with champion/challenger, KServe serving |

Configuration (stations, horizons, storage paths, thresholds) lives in
[configs/base.yaml](configs/base.yaml). The trainee-facing lab guide will be
written once the underlying phases exist.

Contributors and coding agents: read [CLAUDE.md](CLAUDE.md) for the operating
rules before changing anything in this directory.
