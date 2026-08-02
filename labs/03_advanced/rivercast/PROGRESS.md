# RiverCast — Phase Progress

Status values: `not started` · `in progress` · `in review` · `blocked` · `done`.

An agent sets a phase to `in review` when it hands off completed work; the maintainer commits, pushes, opens the PR, links it here, and sets `done` after merging. See `CLAUDE.md` rule 21.

| # | Phase | Status | PR | Notes |
|---|---|---|---|---|
| 0 | Record scope and architecture decisions | in review | [open from `rivercast` branch](https://github.com/MohammadB88/MLOps-Workshop-Exercises/pull/new/rivercast) | ADRs 0001–0003, configs/base.yaml, README educational label |
| 1 | Create the JupyterLab workbench and project skeleton | in review | | Package, typed config, JSON logging, local object store, CLI, envcheck notebook, workbench docs + bootstrap. Maintainer commits/opens PR |
| 2 | Run a data-viability spike | in review | | Gate passed: PROCEED. Spike run live 2026-08-02; UUIDs pinned, fixtures committed, report in docs/data_viability_report.md. Maintainer commits/opens PR |
| 3 | Implement source adapters and immutable raw storage | in review | | PegelOnlineSource + FixtureGaugeSource behind one protocol, shared parser, bronze RawArchive (immutable, checksum-idempotent), ingest flow, contract tests. Maintainer commits/opens PR |
| 4 | Build canonicalization and data-quality contracts | in review | | Silver contracts, normalize (dedup + documented conflict rule), hourly resample (explicit missingness, no interpolation), fail-closed quality checks, DST regression tests on real 2025 fixtures. Maintainer commits/opens PR |
| 5 | Build leakage-safe features and labels | in review | | Lag/rolling/calendar/missingness features, 6h/12h labels, content-hashed dataset manifest, mandatory leakage tests (mutation, label-in-features, centered-window, lag-future checks) all passing. Added pandas/pyarrow/numpy deps. Maintainer commits/opens PR |
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

Phases 0–5 — in review; maintainer commits and opens PRs (one phase per PR). Phase 2's gate decision was PROCEED (docs/data_viability_report.md). Next: Phase 6 (baselines and offline evaluation).

## Blockers

None recorded.
