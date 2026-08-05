# RiverCast failure-mode runbook (Phase 15)

One entry per operational-test scenario in `PLAN.md` Phase 15. Each entry
states what actually happens today (verified against real code, not
aspirational), which test proves it, and what an operator should do. This
is the "a runbook documents each failure" acceptance criterion — every
entry below is a real, cited behavior, not a guess at what a component
"should" do.

Cross-reference: `docs/architecture.md` for the pipeline/component diagram,
`docs/operations.md` for the monitoring/drift/retraining-signal internals,
`docs/instructor_guide.md` for cohort-level reset and known-gaps context.

## PEGELONLINE unavailable

**What happens:** `PegelOnlineSource._get` retries up to
`source.retry.max_attempts` times with exponential backoff (capped at
`backoff_max_seconds`) on network errors and 5xx responses; 4xx responses
fail immediately without retrying (retrying a client error wastes the
budget). After exhausting retries it raises `SourceTimeoutError`, which
propagates up through `components.fetch` as `status="failed"` — the
`rivercast-data-ops` pipeline's `fetch_station_task` returns that status,
`transform_task` runs `.after(*fetch_tasks)` regardless (KFP still runs a
downstream task after an upstream *component* failure as long as the task
itself didn't raise — only a raised exception blocks the DAG), and
`components.validate`'s freshness gate then fails the window because the
affected station has no fresh data, which blocks forecasting for that run
(see "one station stale" below — this is the same mechanism).

**Verified by:** `tests/unit/test_sources.py::test_pegelonline_retries_then_succeeds`,
`::test_pegelonline_timeout_fails_cleanly_after_max_attempts`,
`::test_pegelonline_does_not_retry_client_errors`.

**Operator action:** none required for a transient outage — the next
hourly run retries independently. If PEGELONLINE is down for longer than
`thresholds.data_quality.max_source_staleness_minutes`, forecasting pauses
automatically (fail closed) until fresh data arrives; no forecast is ever
issued from stale input.

## One station stale

**What happens:** `components.validate` computes freshness per station
against `now_utc` and fails the whole validation (`status="failed"`) if the
**target** station (the one the model actually forecasts) is stale beyond
`max_source_staleness_minutes` — a stale non-target upstream station is
recorded but does not by itself fail validation (the target station is
what forecasting depends on directly). `dsl.If(validate.output == "ok")`
in `rivercast_data_ops_pipeline` then skips the `forecast` branch entirely
for that run.

**Verified by:** `tests/unit/test_quality.py::test_freshness_fails_when_stale`,
`tests/unit/test_component_transform_validate.py::test_validate_fails_closed_on_stale_target_station_data`,
`tests/integration/test_data_ops_pipeline.py::test_stale_source_prevents_forecast_generation`.

**Operator action:** check whether the stale station is still returning
data at all (see "PEGELONLINE unavailable"). `monitor` and
`delayed_metrics` still run on a failed validation (they report on
whatever data exists), so the monitoring report for that run is still
useful for diagnosis even though no forecast was issued.

## Malformed measurement

**What happens:** `rivercast.sources.base` parsing rejects a malformed
payload (bad JSON, missing required fields, non-numeric value) with
`MalformedResponseError` before it ever reaches the raw archive or
canonicalization — a malformed response is never silently coerced into a
zero or dropped row.

**Verified by:** `tests/unit/test_sources.py::test_parse_measurements_rejects_malformed`
(parametrized over several malformed shapes), plus malformed-payload cases
in `tests/unit/test_raw_archive.py`.

**Operator action:** none for an isolated malformed response (the retry
loop in `_get` does not apply here — parsing failures aren't retried,
since retrying the same malformed bytes cannot help); if malformed
responses persist across runs, treat it as a PEGELONLINE API contract
change and re-run the Phase 2 data-viability spike before trusting the
source again.

## Object store temporarily unavailable

**What happens:** the local filesystem backend
(`rivercast.storage.object_store.LocalObjectStore`) raises a plain OS-level
exception (`OSError`/`PermissionError`) on a failed read/write, which is
**not** currently caught by a retry wrapper anywhere in `components/` —
every component's outer `try/except Exception` (rule 13: fail closed)
still converts it to `status="failed"` rather than letting it crash the
process uncaught, but there is no automatic retry for a transient
filesystem hiccup today.

**Gap, not yet built:** bounded retry/backoff around object-store I/O
(mirroring `PegelOnlineSource`'s retry loop) is not implemented. Tracked as
a follow-up, not silently assumed to exist — see "Known gaps" below.

**Operator action:** a failed component run is safe to simply re-run
(fetch/transform/train are idempotent or cheaply re-derivable — see
"repeated scheduled run" below); if failures are frequent, check the
underlying disk/mount rather than assuming application-level retry will
mask it.

## MLflow unavailable

**What happens:** every component that talks to MLflow (`trigger`,
`train`, `register`, `promote`, `deploy`, `forecast`) wraps its MLflow
calls inside a broad `try/except` that returns `status="failed"` rather
than raising uncaught (rule 13). Pointed at a real unreachable tracking
URI, `components.deploy.run()` fails closed with the connection error
captured in `result.metadata["error"]`.

**Verified by:** `tests/unit/test_operational_mlflow_unavailable.py::test_deploy_fails_closed_when_mlflow_is_unreachable`
— a real HTTP connection to an unreachable address, not a mocked client.

**Gap, not yet built:** like the object store, there is no bounded
retry/backoff wrapper around MLflow client calls specifically (only
`PegelOnlineSource` has one). A transient MLflow blip currently fails the
whole component run rather than retrying in-process.

**Operator action:** re-run the failed pipeline once MLflow is reachable
again. Because `champion`/`challenger` aliases and prior runs live in
MLflow itself, an outage during `promote` cannot corrupt state — the
promotion transaction only moves `champion` after a real deploy/smoke-test
success (rule 14), so an MLflow outage mid-transaction just means the
transaction never completed, not that it completed wrongly.

## No current champion

**What happens:** `rivercast.models.registry.get_champion` returns `None`
when a registered model has never had a `champion` alias set (rather than
raising). `components.forecast` and the serving layer's `/ready` and
`/predict` both fail closed on a missing champion — serving reports `503`
with an explicit "no champion is set yet" reason rather than a generic
500, and `forecast` returns `status="failed"` rather than fabricating a
prediction from an unset model.

**Verified by:** `tests/unit/test_registry.py::test_get_champion_returns_none_when_no_champion_exists`;
`tests/smoke/test_serving.py` (readiness reporting before any promotion).

**Operator action:** expected, correct state for a fresh environment or
right after `scripts/reset_workshop.sh` — run the model pipeline (or the
training exercises) through a full promotion once before expecting
`/predict` to succeed. Not a bug to debug.

## Deployment readiness timeout

**What happens:** `components.deploy` is a **synchronous** smoke test
(load the model artifact, score one row, check the prediction is finite)
— it has no polling/wait-for-ready loop and therefore no timeout to hit,
because there is no asynchronous readiness state to wait on in this
lab's current deployment target (an in-process model load, not a live
KServe rollout). A real KServe `InferenceService` readiness timeout (the
scenario this line in the plan anticipates) applies once the serving layer
is actually rolled out to a cluster — not yet exercised from this
environment (see "Known gaps").

**Operator action:** if `components.deploy` itself hangs, that indicates
an artifact-loading problem (e.g. a corrupt MLflow artifact store), not a
readiness-timeout scenario — treat it the same as "MLflow unavailable" or
inspect the artifact directly. On a real cluster, a KServe
`InferenceService` stuck in `Unknown`/`False` readiness should be treated
the same as a failed smoke test: `promote_challenger_to_champion` never
moves `champion` unless `deploy_and_smoke_test` explicitly returns `True`
(rule 14), so a stuck rollout cannot silently become the serving champion.

## Candidate endpoint returns invalid output

**What happens:** `components.promote`'s transaction calls
`deploy_and_smoke_test(model_version)` (backed by `components.deploy` in
production wiring); any exception or a `False` return leaves `champion`
untouched and tags the candidate's `deployment_status` as `failed`
(`rivercast.models.registry.promote_challenger_to_champion`). A smoke-test
payload deliberately missing required features reproduces this exactly.

**Verified by:** `tests/integration/test_model_pipeline.py::test_scenario_3_candidate_better_but_deployment_fails_champion_unchanged`.

**Operator action:** none — this is the gate working as intended. Inspect
the failed candidate's MLflow tags (`deployment_status=failed`) to see why
the smoke test failed before manually re-promoting.

## DST transition

**What happens:** the hourly resampling step
(`rivercast.processing.resample`) produces a gap-free, duplicate-free UTC
hourly grid across both a spring-forward and a fall-back transition,
including correctly disambiguating the repeated local hour during
fall-back into two distinct UTC instants (CLAUDE.md rule 6: internal
storage is always UTC).

**Verified by:** `tests/unit/test_dst_regression.py` — real 2025 fixture
data crossing both transitions, not synthetic edge cases.

**Operator action:** none; this is a regression-tested invariant, not an
operational alert.

## Repeated scheduled run

**What happens:** two things make an accidental repeat run cheap and safe
rather than corrupting: (1) `RawArchive.store` is idempotent by content —
an identical raw fetch is detected via its embedded checksum and skipped
rather than duplicated; (2) `components.trigger` skips training when an
MLflow run already exists for the same `dataset_id` + `horizon_hours`.
Phase 15 adds a third layer on top of both: `PipelineRunLock`
(`src/rivercast/concurrency.py`, `components/run_lock/`) refuses to start
a **second concurrent** run of the same pipeline while one is still in
flight, via a `run_lock.acquire` task at the start of both
`rivercast-data-ops` and `rivercast-model`, released through a
`dsl.ExitHandler` so a failure partway through still releases it. A lock
older than 6 hours is treated as abandoned and reclaimed automatically
(a crashed run must not permanently wedge every future scheduled tick).

**Verified by:** `tests/unit/test_concurrency.py`,
`tests/unit/test_component_run_lock.py`,
`tests/integration/test_data_ops_pipeline.py::test_fetch_two_identical_raw_fetches_do_not_duplicate_canonical_observations`.

**Operator action:** if a scheduled run is refused with "pipeline ... is
already running", check whether the previous run is genuinely still in
progress (normal) or crashed without releasing the lock more than 6 hours
ago (should have auto-reclaimed — if it didn't, inspect
`locks/<pipeline-name>.lock.json` in the object store directly).

## Pipeline cancellation and rerun

**What happens:** a cancelled `rivercast-data-ops` or `rivercast-model` run
leaves whatever the completed tasks already wrote (bronze objects, a
partial silver/gold dataset, an MLflow run) exactly as idempotency already
handles it above — a rerun re-derives or skips identical work rather than
duplicating it. The one thing cancellation could previously leave behind
incorrectly is a held run lock blocking every future scheduled tick; the
`dsl.ExitHandler`-wrapped `run_lock.release` task is KFP's mechanism for
running cleanup even when the pipeline is cancelled mid-flight, and the
6-hour staleness reclaim (above) is the backstop if the exit handler itself
never gets to run (e.g. the whole node was killed).

**Verified by:** `tests/unit/test_concurrency.py::test_stale_lock_is_reclaimable`
covers the backstop directly; live KFP-level cancellation semantics
(whether `ExitHandler` actually fires on an operator-cancelled run) are
**not** verified against a real KFP cluster from this environment — see
"Known gaps".

**Operator action:** after cancelling a run, if the next scheduled run is
refused as "already running" sooner than 6 hours later, manually inspect
`locks/<pipeline-name>.lock.json`; if it clearly belongs to the cancelled
run, that is the one case where direct intervention (overwriting the lock
object) is reasonable rather than waiting out the staleness window.

## Known gaps (verified absent, not silently assumed away)

- **No bounded-retry wrapper for object-store or MLflow calls** — only
  `PegelOnlineSource` has one (Phase 3). A transient filesystem or MLflow
  blip fails the current component run closed rather than retrying
  in-process; the next scheduled run (or a manual re-run) recovers.
- **KFP `ExitHandler`/cancellation semantics on a real cluster** are not
  verified from this Windows development environment (same documented
  KFP/Windows `SubprocessRunner` gap as Phases 8-10) — re-verify that
  cancelling a run in the OpenShift AI Pipelines UI actually invokes the
  `run_lock.release` exit task before relying on it in production.
- **Read-only root filesystem, scoped ServiceAccounts/RBAC, and endpoint
  authentication** are not implemented in `deploy/` manifests or the
  FastAPI serving app — see `docs/instructor_guide.md` "Known gaps" and
  the Phase 15 PR description for the full list of cluster-only security
  hardening deferred past this environment's reach.
- **Digest-pinned base images** — Containerfiles reference
  `ubi9/python-311:latest`; the plan's immutable-tag requirement (rule 11)
  is satisfied at deploy-manifest level (`deploy/base/servingruntime.yaml`
  documents the overlay substituting a real digest) but not inside the
  Containerfiles themselves, which stay on a floating base tag pending a
  CI-side digest pin.
- **S3 object-store backend** — unchanged from Phase 14; still not
  implemented, still blocks `configs/openshift.yaml` from running.
