# RiverCast feature specification (Phase 5)

Defines the leakage-safe feature set, label construction, and dataset
manifest. Implementation: `src/rivercast/processing/{features,labels,dataset}.py`.
Interactive walkthrough: `notebooks/02_features_and_leakage.ipynb`.

## 1. Leakage rule

For a row at issue time `t`, every feature uses only hourly observations with
`hour_utc <= t`, for every station including the target. Labels are the one
deliberate exception — they look forward to the exact future value being
predicted, and only that value. This is enforced structurally (`pandas`
`shift()`/backward `rolling()`, never a centered or forward window) and
re-verified by `tests/unit/test_leakage.py`, which is mandatory and maps
1:1 to the plan's leakage rules:

1. mutating observations after `t` must not change the feature row at `t`;
2. label columns must not appear among feature columns;
3. rolling windows must end at `t`, not be centered;
4. lag/upstream features may only reference `hour_utc <= t`.

## 2. Feature columns

One row per hour on the target's own hourly grid (the issue-time index). For
the target station and each configured upstream station, using its
`configs/base.yaml` name lowercased as `{prefix}`:

| Column | Definition |
|---|---|
| `{prefix}_level_t` | value at `hour_utc == t` |
| `{prefix}_lag_1h` / `_lag_3h` / `_lag_6h` | value at `t - 1h` / `t - 3h` / `t - 6h` |
| `{prefix}_delta_1h` | `level_t - lag_1h` |
| `{prefix}_delta_6h` | `level_t - lag_6h` |
| `{prefix}_roll_mean_6h` | mean of `[t-5h .. t]` (backward window, `min_periods=1`) |
| `{prefix}_roll_std_6h` | std of `[t-5h .. t]` (backward window, `min_periods=1`) |
| `missing_{prefix}` | 1 if the station's own hourly grid is missing at `t`, else 0 |

Calendar features (pure functions of `t`, never a data lookup):

| Column | Definition |
|---|---|
| `hour_sin` / `hour_cos` | sine/cosine encoding of hour-of-day (period 24) |
| `day_of_year_sin` / `day_of_year_cos` | sine/cosine encoding of day-of-year (period 365.25) |

A `HistGradientBoostingRegressor`-family model (Phase 6) tolerates `NaN`
feature values natively; lag/rolling columns are `NaN` during the warm-up
window at the start of a fetch and whenever the underlying hourly grid has
`is_missing=True`. `missing_{prefix}` makes that condition explicit and
model-visible rather than silently imputed.

## 3. Labels

```text
target_level_6h  = target station's hourly value at t + 6h
target_level_12h = target station's hourly value at t + 12h
```

A label is populated only when the target station's hourly grid has a
non-missing value at exactly `t + horizon` — the grid is already on the
canonical hourly frequency, so matching is exact-hour lookup rather than a
tolerance search over irregular timestamps. `thresholds.labels
.match_tolerance_minutes` in configuration documents the intended tolerance
for a future irregular-timestamp source (e.g. a DWD forecast feature added in
Extension A); it is accepted by `build_labels()` for interface stability but
is a no-op at the current hourly-grid granularity.

## 4. Rows retained vs. rows used for training

`assemble_dataset()` joins features and labels on issue time and keeps every
row, including the trailing rows near "now" whose future label doesn't exist
yet. `training_rows()` filters to rows where every requested label column is
non-null — those are excluded from training but remain in the full dataset
for live forecasting (Phase 5 acceptance criteria; also needed operationally,
since the live forecast for the current hour has no label yet by definition).

## 5. Dataset manifest and `dataset_id`

`build_manifest()` produces the `DatasetManifest` contract
(`src/rivercast/contracts/features.py`) with the exact fields required by
`PLAN.md` Phase 5. `dataset_id` is `sha256:<hex>`, derived from:

- a row/column-order-independent content hash of the assembled table
  (`pandas.util.hash_pandas_object` over the index-sorted frame);
- schema version, feature version, target/input station UUIDs, horizons, and
  source checksums.

Consequences, verified in `tests/unit/test_dataset.py`:

- identical inputs (same data, same code, same config) always reproduce the
  identical `dataset_id`, regardless of row construction order;
- any change to source data, feature code (`FEATURE_VERSION`), or the input
  checksums changes the ID.

## 6. What Phase 5 does not do

- No object-store wiring for `gold/features/` or `gold/training/dataset_id=<id>/`
  — `build_features`/`build_labels`/`assemble_dataset` are pure functions
  over in-memory data; writing Parquet under those paths is a pipeline-phase
  (8–9) concern, using the `RawArchive`-style storage helpers already built
  in Phase 3.
- No model training — that is Phase 6.
- No cross-validation or temporal split logic — also Phase 6.
