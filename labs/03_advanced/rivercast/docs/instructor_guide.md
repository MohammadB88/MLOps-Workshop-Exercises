# RiverCast instructor guide (Phase 14)

Running RiverCast for a workshop cohort: provisioning, the two supported
modes, failure recoverability, and reset procedures. Trainee-facing content
is `docs/workshop_exercises.md`; this document is instructor-only context
for setting that up and troubleshooting it.

## Provisioning a cohort

Follow `docs/workbench_setup.md` per trainee (or per shared project, if
trainees share one OpenShift AI data science project): a workbench with
persistent storage, `bash scripts/bootstrap_workbench.sh`, and
`rivercast envcheck` to confirm readiness. No cluster-admin rights, no
Docker daemon, and no live PEGELONLINE access are required for any exercise
in `docs/workshop_exercises.md` — every one of them is fixture-mode and
runs fully offline.

Before releasing a cohort image or environment, pin the workbench's Python
environment (either a custom pinned image or the deterministic
`scripts/bootstrap_workbench.sh`) rather than letting trainees install an
unbounded "latest" set of packages — `pyproject.toml`'s runtime and dev
dependencies are already exactly pinned; do not relax that for a workshop
image.

## Instructor/CI mode vs. live mode

| | Instructor/CI mode | Live mode |
|---|---|---|
| Data source | Committed fixtures under `data_fixtures/` | Real PEGELONLINE REST API |
| Storage | Local filesystem (`configs/local.yaml`, gitignored `./artifacts/`) | Local filesystem only today — see limitation below |
| Network required | None | Yes |
| Determinism | Every exercise reproduces the exact same numbers | Depends on real, changing river conditions |
| Config | `configs/local.yaml` (`mode: fixture`) | Copy of `configs/local.yaml` with `mode: live` |

**Instructor/CI mode is the only mode `docs/workshop_exercises.md` assumes.**
It is what CI runs (`.github/workflows/rivercast-ci.yaml`) and what every
exercise's "Expected outcome" was verified against.

**Live mode limitation:** `configs/openshift.yaml` — the config meant to
pair live PEGELONLINE access with persistent, shared OpenShift storage —
requires the S3 object-store backend, which is **not implemented**
(`rivercast.storage.object_store.create_object_store` raises
`ObjectStoreError` for `backend: s3`). Do not advertise a "live mode on
OpenShift AI" exercise to trainees until that backend exists. Live mode
today only works with `mode: live` paired with the **local** storage
backend — real PEGELONLINE data lands on one trainee's own disk, not
shared cluster storage. This is a known, tracked gap, not an oversight to
work around silently; a minimal S3-compatible storage setup exists in a
separate reference repository and can be adapted here once this backend is
implemented.

## Exercise failure recoverability

Every exercise in `docs/workshop_exercises.md` is independently rerunnable
and side-effect-free with respect to the others, with two exceptions worth
flagging to trainees in advance:

- **Exercises 5, 8, 9** write real MLflow runs and, on success, move the
  `champion` alias. Rerunning exercise 8 (rejected candidate) after
  exercise 9 (promoted candidate) is fine — rejection never touches an
  existing champion (rule 14). Rerunning exercise 9 multiple times just
  re-promotes; the promotion transaction is idempotent.
- **Exercise 10** (serving) requires a champion to exist for `/ready` to
  report healthy — if a trainee reaches exercise 10 before 9, seeing a 503
  with `"no champion is set yet"` is the *correct*, documented behavior
  (fail closed, rule 13), not a bug to debug. Point trainees back to
  exercise 9 rather than letting them assume something is broken.

If a trainee's local state gets into a confusing shape (partially-promoted
champion, MLflow runs from an aborted exercise, stale local predictions),
the fix is always the same — see below — not manual surgery on `artifacts/`
or the MLflow tracking database.

## Resetting between attempts or cohorts

```bash
cd labs/03_advanced/rivercast
bash scripts/reset_workshop.sh
```

Removes the local object store (`artifacts/`), local MLflow tracking store
(`mlflow.db`, `mlruns/`, `mlartifacts/`), locally-trained model artifacts
(`models/local/`), and test/build caches — restoring "no champion set for
any horizon" exactly as a fresh clone starts. It never touches anything
tracked by git: fixtures, configs, source code, or committed deliverables
like `reports/baseline/baseline_report.md`. Safe to run between every
trainee attempt or between cohorts; confirmed idempotent (reruns cleanly
when there is nothing left to remove).

This intentionally does **not** reset a live MLflow *server* or shared
object storage if a cohort is later configured against one instead of the
local fixture-mode defaults — it only resets what belongs to the machine or
workbench it runs on.

**Windows troubleshooting:** if the reset fails with
`Device or resource busy` on `artifacts/mlflow.db`, a Jupyter kernel
subprocess from an earlier `nbconvert --execute` or notebook session likely
didn't terminate cleanly and still holds the sqlite file open (observed
during this phase's own verification). Close any running notebook kernels
first, or terminate lingering Python kernel processes, then rerun the
script — it is safe to retry.

## What "done" looks like for one trainee

By the end of `docs/workshop_exercises.md`, a trainee has, entirely
offline:

- inspected real data-quality analysis over real (fixture) PEGELONLINE
  history, including a genuine DST transition;
- verified leakage-safety properties on real feature/label data, not just
  read about them;
- trained and honestly evaluated two real candidate model families against
  a persistence baseline;
- watched a real candidate get rejected and a real candidate get promoted
  through the exact same gated transaction the KFP pipeline uses;
- called a real FastAPI serving endpoint and seen it fail closed before a
  champion exists, then succeed after one is promoted;
- inspected a real delayed-monitoring report naming the exact promoted
  model version, and seen a real synthetic-drift warning and a real
  performance-degradation retraining signal fire under the conditions that
  should trigger them (and stay silent under the conditions that
  shouldn't).

## Known gaps to mention if asked

- **S3 backend not implemented** (see "Live mode limitation" above) — the
  only reason a shared, persistent live deployment on OpenShift AI isn't
  possible today.
- **KServe `InferenceService` readiness/liveness wiring** is defined
  (`deploy/base/inferenceservice.yaml`, `deploy/base/servingruntime.yaml`)
  but not verified against a real cluster from this development
  environment — see `docs/pipeline_components.md` and
  `tests/smoke/test_serving.py`'s module docstring for exactly what was and
  wasn't verified.
- **KFP `SubprocessRunner` full execution** was not verifiable from the
  Windows development environment this lab was built in (a KFP/Windows
  shell incompatibility, unrelated to RiverCast's own code) — re-verify
  pipeline submission in the actual Linux JupyterLab workbench before
  trusting exercise 6/7 beyond what's documented there.
