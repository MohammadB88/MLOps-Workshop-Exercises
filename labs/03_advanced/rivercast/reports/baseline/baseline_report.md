# Baseline training report (Phase 6)

- **Generated:** 2026-08-02, from `notebooks/03_baseline_training.ipynb` /
  `rivercast train`, fixture mode.
- **Dataset:** `sha256:ba84a157938ef1be2f5176cd16668894d031c2b15bb4230a1781a9e8c7b46aef`
  (168 hourly rows, 2024-08-01 → 2024-08-08, KAUB target, MAINZ/OESTRICH/BINGEN
  upstream — the committed Phase 2/3 fixture overlap window).
- **Split:** chronological, train=oldest 70% / validation=next 15% /
  test=newest 15% (`rivercast.models.split.temporal_split`).
- **Seed:** 42 for both candidates.

## Results

| Horizon | Model | Test MAE (cm) | Persistence MAE (cm) | Skill vs. persistence | Beats persistence? |
|---|---|---|---|---|---|
| 6h | ridge | 0.76 | 3.24 | **+0.767** | **YES** |
| 6h | hist-gradient-boosting | 7.52 | 3.24 | −1.319 | no |
| 12h | ridge | 4.23 | 6.17 | **+0.314** | **YES** |
| 12h | hist-gradient-boosting | 11.14 | 6.17 | −0.806 | no |

## Honest conclusion

Ridge **beats persistence at both configured horizons** on this dataset —
the Phase 6 acceptance criterion ("the model beats persistence for at least
one configured horizon, or the report honestly concludes that it does not")
is satisfied by ridge.

`hist-gradient-boosting` **does not** beat persistence here and is reported
as such rather than hidden. The cause is not a training bug: the fixture
dataset has only 168 rows (112 train / 24 validation / 25 test), and
`HistGradientBoostingRegressor`'s larger effective capacity (`max_iter=200`,
`max_depth=6`) overfits on a sample this small — it improves over persistence
on the validation split at 6h (skill +0.662) but degrades sharply on the
smaller, chronologically later test split. This is the expected failure mode
of a flexible model on a short bootstrap window, not evidence against the
model family; the Phase 2 spike's recommended production bootstrap window
(2023 → present, ~3.6 years) is orders of magnitude larger and is where
`hist-gradient-boosting` is expected to become competitive per the plan's
model ladder (§2.4).

## Reproducibility

Training twice with the same seed (42) and the same dataset produces
identical `dataset_id` and identical test-set MAE
(`0.7558233948649763 == 0.7558233948649763` for ridge/6h) — verified in the
notebook and in `tests/unit/test_local_pipeline.py::test_run_training_is_reproducible_for_same_seed`.

## Serialization parity

Predictions from a freshly trained model and predictions from the same model
reloaded from its `joblib` artifact are bit-identical
(`predictions_match(...) == True`) — verified in the notebook and in
`tests/unit/test_package.py`.

## Leakage review signal

A deliberately leaked model (label value smuggled into the feature set) is
demonstrated in `tests/unit/test_leaked_model_detection.py`: MAE collapses to
well under persistence's error and skill jumps above 0.8 even without a
recognizably named leak column — this is the signature a maintainer's review
of a baseline report like this one should treat as disqualifying, regardless
of how good the skill number looks.

## What this report does not cover

- Slice metrics (season, rising/falling water, quantile bands) — the
  `evaluate` module supports them
  (`rivercast.models.evaluate.rising_falling_slices`,
  `water_level_quantile_slices`), but the 7-day fixture window is too short
  for seasonal slices to be meaningful; slice reporting becomes useful once
  the multi-year production dataset is materialized (Phases 8-9).
- MLflow tracking and registry — Phase 7.
- Promotion decisions — the promotion policy (`configs/base.yaml`
  `thresholds.promotion`) is evaluated by the model pipeline in later phases,
  not by this offline report.
