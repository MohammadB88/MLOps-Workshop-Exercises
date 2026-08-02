# RiverCast model card (Phase 6-7)

> **Educational system.** These models must never be used for navigation,
> flood protection, or any real-world decision. PEGELONLINE water level is
> relative to the local gauge zero, not river depth.

## Task

Forecast the water level (`W`, cm relative to local gauge zero) at **KAUB on
the Rhine**, 6 hours and 12 hours ahead, on an hourly canonical grid. One
model per horizon, registered in MLflow as `rivercast-kaub-6h` /
`rivercast-kaub-12h` (Phase 7).

## Inputs

Leakage-safe hourly features from `rivercast.processing.features.build_features`
(full spec: `docs/feature_spec.md`) — lags, rolling statistics, and
missingness indicators for KAUB and its three upstream inputs (MAINZ,
OESTRICH, BINGEN), plus calendar encodings. No DWD weather data in this MVP
(ADR 0001).

## Model families

| Model | Status | Notes |
|---|---|---|
| Persistence (`ŷ(t+h) = level(t)`) | baseline, mandatory comparison | `rivercast.models.baseline.PersistenceModel` |
| Ridge regression | candidate | `StandardScaler` + `SimpleImputer(median)` + `Ridge(alpha=1.0)`, seeded |
| `HistGradientBoostingRegressor` | candidate | native NaN handling, `max_iter=200`, `max_depth=6`, `learning_rate=0.05`, seeded |

No deep learning in the MVP (ADR 0001). Both candidates are fit only on the
chronological training split (`rivercast.models.split.temporal_split`);
Ridge's imputer/scaler are fit on that same split only, never on
validation/test.

## Evaluation

- **Metrics:** MAE and RMSE in centimeters; skill vs. persistence
  (`1 - candidate_mae / persistence_mae`). MAPE is deliberately not used —
  low/near-zero gauge values make it unstable.
- **Split:** chronological — train (oldest 70%), validation (next 15%), test
  (newest 15%). No shuffling.
- **Slices:** rising/falling water and level-quantile bands are implemented
  (`rivercast.models.evaluate`); season slicing and full reporting are
  meaningful once a multi-year dataset exists (Phases 8-9).

## Current results (fixture-mode bootstrap)

See `reports/baseline/baseline_report.md` for the full report. Summary: on
the small 168-row fixture window, **ridge beats persistence at both 6h and
12h** (skill +0.77 and +0.31 on the test split); `hist-gradient-boosting`
overfits on this small sample and does not beat persistence — reported
honestly rather than hidden, with the expectation that it becomes competitive
on the full multi-year bootstrap dataset (Phase 2 spike recommendation:
2023 → present).

## Reproducibility and integrity guarantees

- Same seed + same data → identical `dataset_id` and identical metrics
  (`tests/unit/test_local_pipeline.py`).
- Predictions before and after `joblib` serialization are bit-identical
  (`tests/unit/test_package.py`).
- `train_candidate` refuses to train on a feature frame containing a
  `target_level_*` column — a structural leakage guard
  (`rivercast.models.train`, `tests/unit/test_leaked_model_detection.py`).
- A leaked model (label encoded under an innocuous feature name) is shown to
  produce suspiciously perfect skill (>0.8, MAE far below persistence) — the
  signature a review of this model card / the baseline report should treat
  as disqualifying.

## Tracking and registry (Phase 7)

Every training run is logged to MLflow (`rivercast.models.tracking.log_training_run`)
with: parameters, headline and slice metrics, the feature list, a dataset
manifest, the model signature and an input example, and tags for Git commit,
container image digest (once Phase 8 exists), station UUIDs, `dataset_id`,
`horizon_hours`, `validation_status`, and `deployment_status`. The tracking
URI is resolved from the `MLFLOW_TRACKING_URI` environment variable when
set, falling back to a local sqlite store under `storage.root`
(`configs/base.yaml` `mlflow.tracking_uri_default`) so fixture-mode
workbenches and CI need no live server (`rivercast.models.tracking.resolve_tracking_uri`).

Registered artifacts are versions of `rivercast-kaub-6h` /
`rivercast-kaub-12h`. Promotion follows a strict transaction
(`rivercast.models.registry.promote_challenger_to_champion`): register →
assign `challenger` → validate the deployable artifact → deploy to a
non-production endpoint → smoke test → only then move `champion`. A failed
or raising deploy/smoke-test step leaves the existing `champion` untouched
(CLAUDE.md rule 14) — real deployment arrives in Phases 8-11, so the current
deploy/smoke-test step is an injectable stub (`_always_pass_smoke_test`)
that a caller can replace, as demonstrated with a deliberately failing stub
in `notebooks/04_mlflow_tracking.ipynb`.

Promotion gates (`rivercast.models.registry.evaluate_promotion_gates`,
thresholds from `configs/base.yaml` `thresholds.promotion`) compare a
candidate's test-split metrics against the **current champion's real logged
metrics**, reconstructed from its MLflow run
(`rivercast.models.registry.champion_test_report`) — not a placeholder. Three
checks must all pass: skill vs. persistence, MAE regression vs. champion
(bounded), and no slice regressing beyond the configured fraction. A
rejected candidate is still registered (traceable) and tagged
`validation_status=rejected`; it never receives the `champion` alias. The
first model for a horizon has no champion to compare against, so only the
skill-vs-persistence check applies (first-model bootstrap).

## Known limitations (Phase 7 scope)

- Trained and evaluated only against the small fixture bootstrap window; not
  yet run against the full historical dataset from the Phase 2 spike.
- The deploy/smoke-test step in the promotion transaction is a stub
  (always succeeds by default) until Phases 8-11 add real serving; no actual
  endpoint is deployed yet.
- No slice-based promotion checks are exercised against real multi-slice
  data yet — the fixture window is too short for season slices to be
  meaningful (same caveat as `reports/baseline/baseline_report.md`).
- No scheduled/automatic retraining yet (Phase 10 and Phase 12's retraining
  signal).
