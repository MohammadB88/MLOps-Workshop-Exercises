# RiverCast operations: delayed monitoring and retraining signals (Phase 12)

`rivercast.monitoring` adds three modules on top of Phase 9's plain
delayed-metrics join (`rivercast.processing.delayed_metrics`), wired into
`components.monitor`:

| Module | Produces | Never does |
|---|---|---|
| `monitoring.data_quality` | Freshness/coverage/missingness summary (existing Phase 4/8 checks) plus an Evidently `DataSummaryPreset` snapshot | Block a pipeline run — that gate is `components.validate`, not `monitor` |
| `monitoring.drift` | Feature drift over a reference/current split of the gold dataset, via Evidently `DataDriftPreset` | Trigger retraining by itself (ADR 0003) |
| `monitoring.performance` | Delayed MAE/RMSE, error-vs-persistence, rising/falling and level-quantile slices, an Evidently `RegressionPreset` snapshot, and the retraining-decision artifact | Move the `champion` alias — only `components.promote`'s smoke-tested transaction does that (rule 14) |

## Evidently version note

The plan's reference links describe Evidently's legacy API
(`evidently.report.Report`, `evidently.metric_preset.*`). That module was
**removed** in the 0.7 rewrite this lab is pinned to (`evidently==0.7.21`).
The current API is `evidently.Report` + `evidently.presets.*`, and a preset
needs the raw pandas DataFrame (for `DataDriftPreset`/`DataSummaryPreset`)
or an `evidently.Dataset` wrapped with `DataDefinition(regression=...)`
column roles (for `RegressionPreset`) — confirmed by running each preset
against real data before writing any production code, not assumed from the
docs. `snapshot.dict()`/`snapshot.json()`/`snapshot.save_html()` on the
returned `Snapshot` are the same shape either way.

## Delayed performance monitoring

`components.monitor` now loads every persisted `PredictionRecord` per
configured horizon, joins them against the silver hourly grid
(`rivercast.processing.delayed_metrics.join_matured_predictions`, unchanged
from Phase 9 — never fabricates a missing observation), and if the horizon
has a champion with a logged evaluation, builds a
`RollingPerformanceReport`:

- `overall` — plain MAE/RMSE via `calculate_delayed_metrics`, `n_matured`
  vs. `n_total` so a report never hides how many predictions are still
  unmatured;
- `error_vs_persistence_mae_cm` — rolling MAE minus the champion's own
  training-time persistence MAE (`champion_test_report`, Phase 7);
- `slices` — rising/falling and level-quantile buckets, reusing
  `rivercast.models.evaluate.{rising_falling_slices,water_level_quantile_slices}`
  (renamed from private `_mae`/`_rmse` to public `mae_cm`/`rmse_cm` in that
  module so this package could reuse them instead of duplicating the same
  MAE/RMSE arithmetic a second time);
- `evidently_snapshot_json` — a `RegressionPreset` snapshot, or `None` when
  fewer than 2 matured predictions exist (Evidently's own R² metric is
  undefined below that; the plain MAE/RMSE above are unaffected).

## The retraining-decision artifact

`rivercast.monitoring.performance.evaluate_retraining_signal` implements
the plan's Phase 12 schema exactly:

```json
{
  "requested": true,
  "reasons": ["rolling_mae_degraded: 10.00cm >= 3.60cm (1.2x persistence)"],
  "reference_model_version": "7",
  "new_labeled_rows": 30,
  "created_at_utc": "..."
}
```

It fires on exactly one condition — rolling delayed MAE at or above
`thresholds.monitoring.performance_degradation_mae_ratio` times the
champion's own persistence-baseline MAE — and is withheld
(`requested=False`) whenever fewer than
`thresholds.monitoring.min_matured_predictions_for_signal` predictions have
matured, even if the ratio would otherwise trip: a small-sample rolling MAE
is not trustworthy evidence on its own. Drift never appears as a reason
here (ADR 0003: *"Do not retrain solely because feature drift is
detected"*) — `monitoring.drift`'s output is written to the same monitoring
report as an advisory `is_warning` flag, entirely separate from this
decision.

`components.trigger` (Phase 10) is unchanged and still gates the
`rivercast-model` pipeline's actual training step independently
(`min_new_labeled_rows`, duplicate-dataset check). The retraining-decision
artifact is a signal a human or a future automation can read from the
monitoring report; it does not short-circuit `trigger`'s own gate, matching
the plan's explicit instruction that "the scheduled model pipeline reads
this signal but still re-runs all data and model gates."

## Drift reporting

`monitoring.drift.run_drift_report` splits the current gold dataset in
half (oldest half as reference, newest half as current) and runs
`DataDriftPreset` over the feature columns, extracting the
`DriftedColumnsCount` metric's `share` value as `drifted_share`. A share
above `thresholds.monitoring.drift_share_warning_threshold` (default 0.5)
sets `is_warning=True` in the monitoring report — advisory only, per the
table above. Fails closed (raises `ValueError`) on an empty reference,
empty current, or missing column, rather than silently reporting "no
drift" over data that was never actually compared.

## Monitoring report shape

`components.monitor` writes one JSON report per run to
`reports/monitoring/<silver-window>_monitor.json`:

```text
{
  "checked_at_utc": ...,
  "silver_key": ...,
  "row_count": ..., "missing_station_count": ..., "missing_stations": [...],
  "by_station": { "<station_uuid>": {"row_count": ..., "staleness_minutes": ...}, ... },
  "delayed_by_horizon": [
    {
      "horizon_hours": 6,
      "performance": {"n_matured": ..., "mae_cm": ..., "error_vs_persistence_mae_cm": ..., ...} | null,
      "drift": {"drifted_share": ..., "is_warning": ...} | null,
      "retraining_signal": {"requested": ..., "reasons": [...], ...} | null
    },
    ...
  ]
}
```

The three `delayed_by_horizon` sections are independently `null` until
their prerequisites exist (a champion with a logged evaluation for
`performance`/`retraining_signal`; at least 4 gold-dataset rows for
`drift`) — a fresh fixture window before any model is promoted produces a
report with every section `null` rather than failing (plan §Phase 12
acceptance: *"Reports work with no labels and with delayed labels"*,
verified in `tests/integration/test_monitor_delayed_signals.py`).

## What is and isn't tested here

`tests/unit/test_monitoring_{drift,performance,data_quality}.py` test each
module in isolation against synthetic data, including the plan's specific
acceptance fixtures: a synthetic drift fixture crossing the warning
threshold, a genuine performance-degradation fixture that requests
retraining, and a too-few-matured-predictions fixture that withholds the
signal even though the ratio alone would trip.
`tests/integration/test_monitor_delayed_signals.py` exercises the same
logic through `components.monitor` against a real trained, registered, and
promoted champion and a real matured forecast — confirming the monitoring
report names the actual champion model version (not a placeholder) and
that a monitor run reporting drift never itself moves the `champion` alias
(the promotion-gates acceptance criterion).

Not verified here (needs a live cluster, out of scope for this
environment): Evidently HTML reports rendered and inspected in an actual
OpenShift AI workbench; a real multi-week rolling window against live
PEGELONLINE data.
