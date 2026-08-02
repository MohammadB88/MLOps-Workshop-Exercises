# ADR 0002 — Data versioning: immutable raw zones, object-storage layout, dataset manifests, fixture mode

- **Status:** accepted
- **Date:** 2026-08-02
- **Deciders:** RiverCast maintainers
- **Related:** [ADR 0001](0001-rivercast-scope.md), [ADR 0003](0003-pipeline-boundaries.md), `PLAN.md` §3–5, Phase 3–5

## Context

A continuous-training loop is only trustworthy if every dataset and model can be
traced back to exactly which source responses, code, and configuration produced
it — and if reruns cannot silently rewrite history. Sensor data arrives late, is
revised, and has gaps; CI and workshops must run without internet access.

## Decision

1. **Zoned object-storage layout.** All data artifacts live in an S3-compatible
   object store (local filesystem implements the same interface for development)
   under six zones:

   ```text
   bronze/        raw source responses, immutable, partitioned by
                  source / parameter / station_uuid / event_date
   silver/        normalized + hourly-resampled canonical observations
   gold/          feature tables and versioned training datasets
   predictions/   issued forecasts with model + dataset lineage
   reports/       data-quality, monitoring, and evaluation reports
   models/        exported model artifacts for serving
   ```

2. **Raw data is immutable.** A raw response is written once, keyed by fetch
   timestamp and content checksum, with source metadata (endpoint, requested
   window, HTTP status, ETag, SHA-256, code commit). Re-fetching the same window
   appends a new raw object; it never overwrites. Deduplication happens during
   normalization, not by mutating bronze.
3. **Timestamps are stored in UTC** internally; the original source timestamp
   and offset are preserved alongside. Hourly resampling takes the last valid
   reading at or before the hour within a configured tolerance and emits explicit
   missingness indicators — large gaps are never interpolated silently.
4. **Versioned training datasets via manifests.** Every training dataset is
   identified by a content-derived `dataset_id` and described by a manifest
   recording: source window, station UUIDs, horizons, row count, schema version,
   feature version, source checksums, Git commit, and image digest. A model is
   traceable to its dataset via this ID; the dataset is traceable to bronze via
   checksums.
5. **Parquet + DuckDB/PyArrow for querying.** No database in the MVP. Canonical
   and feature data are Parquet; local querying uses DuckDB or PyArrow.
6. **Fixture mode is the default.** Every live source adapter has a deterministic
   fixture adapter with the identical output schema, backed by committed fixture
   data under `data_fixtures/`. Workshops and CI run in fixture mode; live
   PEGELONLINE access is opt-in configuration.

## Consequences

- Reruns are idempotent downstream of bronze: the same raw inputs always produce
  byte-equivalent canonical output, and duplicate fetches cannot corrupt history.
- Storage grows monotonically in bronze; a retention/lifecycle policy is deferred
  to the hardening phase (Phase 15) and must never apply to data referenced by a
  registered model's manifest.
- Unit tests make zero network calls; the full workshop works offline.
- Late or revised observations become new rows selected by a documented conflict
  rule and flagged — never silent updates.
