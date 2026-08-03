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
| 6 | Establish baselines and offline evaluation | in review | | Temporal split, persistence/ridge/HistGradientBoosting, MAE/RMSE/skill + slice metrics, serialization parity, `rivercast train` CLI. Ridge beats persistence at both horizons on the fixture dataset; HGB honestly reported as not beating it (overfits on 168 rows) — see reports/baseline/baseline_report.md. Added scikit-learn dep. Maintainer commits/opens PR |
| 7 | Add MLflow tracking and registry | in review | | Full run logging (params/metrics/slices/manifest/signature/tags) via `rivercast.models.tracking`; registry + challenger/champion promotion transaction via `rivercast.models.registry` (bootstrap, idempotent registration, real champion-metrics comparison, deploy-failure never moves champion). `rivercast train --track-mlflow`/`--promote` CLI flags. Downgraded pandas 3.0.5 → 2.3.3 (mlflow's own metadata caps pandas <3 on every current release); re-ran full Phase 4-6 suite with no regressions. Local sqlite tracking-URI default added so fixture mode needs no live server. Maintainer commits/opens PR |
| 8 | Containerize reusable pipeline components | in review | | 10 components (`fetch`, `transform`, `validate`, `train`, `evaluate`, `register`, `promote`, `forecast`, `monitor`, `deploy`), each a plain `run()` function + thin CLI, reading/writing via object-store keys, small JSON result envelope, fail-closed. `tests/integration/test_components_end_to_end.py` runs the full chain against real (isolated) object storage + MLflow. Found and fixed two real upstream/pre-existing bugs: an MLflow-on-Windows `models:/` URI resolution bug (worked around via `runs:/<run_id>/model`, see `docs/pipeline_components.md`) and a Phase 7 gap where a fresh sqlite-backed MLflow experiment defaulted its artifact store to the process CWD instead of the isolated storage root. Four Containerfiles (`rivercast-data/train/ops/serving`), non-root (UID 1001); `pip install .` + each entrypoint verified against a clean staged copy (no Docker daemon available here, per CLAUDE.md rule 19). KFP compatibility verified at the component-signature and compile level; full `SubprocessRunner` execution not verifiable on this Windows dev box (documented, re-verify in the Linux workbench at Phase 9). Added `kfp` dev dependency. Maintainer commits/opens PR |
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

Phases 0–8 — in review; maintainer commits and opens PRs (one phase per PR). Phase 2's gate decision was PROCEED (docs/data_viability_report.md). Next: Phase 9 (implement the `rivercast-data-ops` pipeline).

## Blockers

None recorded.
