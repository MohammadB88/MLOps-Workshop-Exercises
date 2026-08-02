# RiverCast data contract (Phase 4)

Defines the silver-layer schemas, the resampling rule, and the data-quality
checks that gate everything downstream. Implementation:
`src/rivercast/contracts/hourly.py`, `src/rivercast/processing/`.

## 1. Canonical (native-cadence) schema

One row per `(station_uuid, observed_at_utc, parameter)`, produced by
`normalize_measurements()` from raw `Measurement` records (bronze → silver).

| Column | Type | Notes |
|---|---|---|
| `station_uuid` | str (UUID) | immutable PEGELONLINE identifier |
| `station_name` | str | display name, informational only |
| `water_body` | str | e.g. `RHEIN` |
| `parameter` | str | `W` in the MVP |
| `observed_at_utc` | datetime (UTC) | internal storage axis (rule 6) |
| `source_offset` | str | original offset, e.g. `+02:00` (rule 7) |
| `value` | float | cm relative to local gauge zero |
| `unit` | str | `cm` |
| `quality_status` | str | `ok` \| `conflict` |
| `ingested_at_utc` | datetime (UTC) | when this fetch was ingested |
| `source_sha256` | str | links back to the bronze raw object |
| `schema_version` | int | `1` |

## 2. Hourly (resampled) schema

One row per `(station_uuid, parameter, hour_utc)` on the canonical hourly
grid, produced by `resample_hourly()`.

| Column | Type | Notes |
|---|---|---|
| `station_uuid` | str (UUID) | |
| `station_name` | str | |
| `parameter` | str | |
| `hour_utc` | datetime (UTC) | exactly on the hour |
| `value` | float \| null | null when `is_missing` |
| `is_missing` | bool | explicit — never silently interpolated |
| `source_lag_minutes` | float \| null | distance from `hour_utc` back to the reading used |
| `schema_version` | int | `1` |

## 3. Resampling rule

For each target hour `h`: use the **last valid reading at or before `h`**
within `thresholds.data_quality.resample_tolerance_minutes` (30 min in
`configs/base.yaml`). If none exists in that window, the hour is
`is_missing=True` — large gaps stay explicit and are never filled by
interpolation, forward-fill, or any other default. Native 15-minute data is
untouched; the hourly table is a derived view alongside it.

## 4. Conflict resolution

A **conflict** is two different values for the same natural key
`(station_uuid, observed_at_utc, parameter)` — typically a later fetch
revising an earlier reading. Rule (`processing/normalize.py`): **the larger
value wins**, deterministically, and the row is tagged `quality_status
="conflict"`. Both raw observations remain readable in bronze; the losing
value is recorded in a `ConflictRecord` for the data-quality report — never
silently dropped. Conflicts alone are a `warning`, not a pipeline-stopping
`error` (see §5); they still surface for review because a conflict most often
signals a sensor revision worth checking.

## 5. Data-quality checks (`processing/quality.py`)

`run_checks()` aggregates checks into a `QualityReport`. Only `severity=
"error"` blocks the pipeline (rule 13: fail closed); `"warning"` issues are
recorded but do not stop training or promotion by themselves.

| Check | Severity | Trigger |
|---|---|---|
| `value_bounds` | error | value outside `thresholds.data_quality.value_bounds_cm` |
| `monotonic_timestamps` | error | unsorted or duplicate `observed_at_utc` within one station+parameter after normalization |
| `station_coverage` | error | a required station has zero observations |
| `freshness` | error | latest observation older than `max_source_staleness_minutes`, or no data at all |
| `short_gap_missingness` | warning | a run of missing hours exceeds `max_short_gap_minutes` |
| `conflicts` | warning | any conflicting duplicates were resolved during normalization |

A malformed raw payload never reaches these checks at all — it is rejected by
`parse_measurements()` in Phase 3 and archived for diagnosis without being
promoted (see `docs/adr/0002-data-versioning.md`).

## 6. DST correctness

Timestamps are parsed with their explicit source offset and converted to UTC
before any comparison, deduplication, or resampling. Verified against the
real PEGELONLINE fixtures for both 2025 transitions
(`tests/unit/test_dst_regression.py`, using
`data_fixtures/pegelonline/historical/dst_spring_2025_KAUB.json` and
`dst_fall_2025_KAUB.json`):

- **Spring-forward** (`02:00 CET` skips to `03:00 CEST`): resamples to a
  gap-free, strictly-increasing hourly UTC grid with no missing hours.
- **Fall-back** (`02:00–03:00` occurs twice, once CEST once CET): the two
  local-time-identical readings normalize to two distinct UTC instants — not
  a duplicate, not a conflict — and the hourly grid stays gap-free.

## 7. What Phase 4 does not do

- No feature engineering or label construction — that is Phase 5.
- No cross-station joins beyond independent per-station resampling.
- No object-store wiring for the silver zone — `resample_hourly()` and
  `run_checks()` are pure functions over in-memory lists; the pipeline phases
  (8–9) are what call them against bronze/silver paths in the object store.
