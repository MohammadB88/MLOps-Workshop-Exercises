# RiverCast — Phase Progress

Status values: `not started` · `in progress` · `in review` · `blocked` · `done`.

An agent may set a phase to `in review` when it opens a PR for it. Only the maintainer sets a phase to `done`, and only after merging. See `CLAUDE.md` rule 21.

| # | Phase | Status | PR | Notes |
|---|---|---|---|---|
| 0 | Record scope and architecture decisions | in review | [open from `rivercast` branch](https://github.com/MohammadB88/MLOps-Workshop-Exercises/pull/new/rivercast) | ADRs 0001–0003, configs/base.yaml, README educational label |
| 1 | Create the JupyterLab workbench and project skeleton | not started | | |
| 2 | Run a data-viability spike | not started | | Gate — do not build pipelines until the source is proven usable |
| 3 | Implement source adapters and immutable raw storage | not started | | |
| 4 | Build canonicalization and data-quality contracts | not started | | |
| 5 | Build leakage-safe features and labels | not started | | |
| 6 | Establish baselines and offline evaluation | not started | | |
| 7 | Add MLflow tracking and registry | not started | | |
| 8 | Containerize reusable pipeline components | not started | | |
| 9 | Implement `rivercast-data-ops` pipeline | not started | | |
| 10 | Implement `rivercast-model` pipeline | not started | | |
| 11 | Build the serving layer | not started | | |
| 12 | Implement delayed monitoring and retraining signals | not started | | |
| 13 | Add CI and release automation | not started | | |
| 14 | Integrate with the workshop learning flow | not started | | |
| 15 | Harden before calling it complete | not started | | |
| A | Extension — Add DWD observations | not started | | Only after the gauge-only loop works |
| B | Extension — Add DWD ICON-D2 forecasts | not started | | Advanced data-engineering exercise |
| C | Extension — Multi-station models | not started | | |
| D | Extension — Canary rollout | not started | | After direct replacement works reliably |

## Current phase

Phase 0 — in review (PR opened; awaiting maintainer review). Phase 1 starts after merge.

## Blockers

None recorded.
