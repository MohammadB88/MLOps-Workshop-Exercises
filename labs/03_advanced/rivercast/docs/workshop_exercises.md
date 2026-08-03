# RiverCast workshop exercises (Phase 14)

A trainee sequence through the finished RiverCast lab, in the OpenShift AI
JupyterLab workbench (or any machine after `bash scripts/bootstrap_workbench.sh`
— see `docs/workbench_setup.md`). Every step below runs in **instructor/CI
mode**: fixture data, local storage, no internet access, no credentials.
**Live mode** (real PEGELONLINE requests) is available as an opt-in variant
of exercises 1–2 only — see "Live mode" at the end of this document, and its
current limitation.

Each exercise names the exact command or notebook to run and what you should
observe. If your result doesn't match "Expected outcome," something is
genuinely wrong — that's the point of a workshop with deterministic fixtures.

## 1. Environment check

```bash
source .venv/bin/activate
rivercast envcheck
```

Then open `notebooks/00_environment_check.ipynb`, select the **Python
(rivercast)** kernel, and **Restart Kernel and Run All Cells**.

**Expected outcome:** package import, configuration, and writable-storage
checks `PASS`. Fixture access `PASS`. MLflow/KFP/cluster-API checks `WARN` if
those services aren't attached to your workbench — that's expected outside a
fully configured OpenShift AI project, not a failure of the lab itself.

## 2. Explore source data and quality

Open `notebooks/01_source_and_data_quality.ipynb`, **Restart Kernel and Run
All Cells**.

**Expected outcome:** the notebook answers every Phase 2 gate question
against the committed fixtures — station identity/UUIDs, observation
cadence, missing intervals, duplicates, DST spring-forward/fall-back
transitions, and station overlap — and reproduces the PROCEED decision
already recorded in `docs/data_viability_report.md`. Every number is
deterministic; rerunning must reproduce the exact same figures.

## 3. Inspect leakage-safe features

Open `notebooks/02_features_and_leakage.ipynb`, **Restart Kernel and Run All
Cells**.

**Expected outcome:** the feature table for KAUB (lags, rolling stats,
upstream levels, calendar encodings, missingness flags) and the 6h/12h
labels. The notebook demonstrates each mandatory leakage property from
`CLAUDE.md` rule 8 directly on real data: mutating an observation after
issue time `t` does not change the feature row at `t`; labels never appear
among the feature columns; rolling windows end exactly at `t`.

## 4. Train persistence and candidate models

Open `notebooks/03_baseline_training.ipynb`, **Restart Kernel and Run All
Cells** — or from the terminal:

```bash
rivercast train --horizon 6 --model ridge
rivercast train --horizon 6 --model hist-gradient-boosting
```

**Expected outcome:** MAE/RMSE/skill-vs-persistence for both candidates at
both horizons, reproducing `reports/baseline/baseline_report.md`. On this
fixture dataset, ridge beats persistence at both horizons;
hist-gradient-boosting does not (it overfits on the fixture window's ~160
training rows) — the report states this honestly rather than picking
whichever number looks better. Training twice with the same `--seed`
produces identical metrics.

## 5. Compare runs in MLflow

Open `notebooks/04_mlflow_tracking.ipynb`, **Restart Kernel and Run All
Cells** — or:

```bash
rivercast train --horizon 6 --model ridge --track-mlflow
```

**Expected outcome:** a new MLflow run under the `rivercast` experiment with
parameters, metrics, slice metrics, dataset manifest, model signature, and
the serialized model. `--track-mlflow` alone only logs and registers a
candidate version — it does **not** move the `champion` alias. Add
`--promote` to attempt promotion through the CLI's own gate check; unlike
the KFP pipeline's `promote` component (exercise 8), the CLI path's
deploy/smoke-test step is a stub that always passes
(`rivercast.models.mlflow_pipeline._always_pass_smoke_test`) — real
deployment validation only happens in the pipeline.

## 6. Compile and inspect the pipelines

Open `notebooks/05_pipeline_development.ipynb`, **Restart Kernel and Run All
Cells** — or:

```bash
python -m pipelines.data_ops_pipeline
python -m pipelines.model_pipeline
```

**Expected outcome:** `pipelines/compiled/rivercast-data-ops.yaml` and
`rivercast-model.yaml` (re)compiled with no diff against the committed
copies (CI enforces this — see `.github/workflows/rivercast-ci.yaml`). The
notebook also runs every pipeline step as a plain function call, so you see
each stage's real output before trusting the compiled DAG.

## 7. Run the full component chain (the pipeline's actual behavior, offline)

```bash
python -m pytest tests/integration/test_components_end_to_end.py -v
```

**Expected outcome:** fetch → transform → validate → monitor → train →
evaluate → register → promote → deploy → forecast, in sequence, against
real (isolated) fixture data and an isolated MLflow tracking store — the
same chain the compiled `rivercast-data-ops`/`rivercast-model` pipelines
run, exercised without needing a live KFP cluster. This is the most direct
way to see the whole loop work end to end in this environment.

## 8. Observe a deliberately rejected candidate

```bash
python -m pytest tests/integration/test_model_pipeline.py -v -k scenario_2
```

**Expected outcome:** `test_scenario_2_candidate_worse_than_champion...`
passes, demonstrating that a candidate failing the promotion gates
(`thresholds.promotion` in `configs/base.yaml`) is registered and tagged
`validation_status=rejected` but never receives the `champion` alias — the
existing champion (if any) is untouched.

## 9. Observe a legitimate promotion

```bash
python -m pytest tests/integration/test_model_pipeline.py -v -k scenario_4
```

**Expected outcome:** `test_scenario_4_candidate_passes_and_endpoint_works...`
passes: register → challenger → real deploy/smoke-test (via
`components.deploy`) → champion transaction completes, and the promoted
version is confirmed as the new champion by alias lookup.

## 10. Call the serving endpoint

```bash
RIVERCAST_CONFIG=configs/local.yaml RIVERCAST_LAB_ROOT=. \
  python -m uvicorn rivercast.serving.app:app --port 8080
```

In another terminal:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:8080/metadata
```

**Expected outcome:** `/health` always returns `{"status": "ok"}`. `/ready`
returns HTTP 503 with `"ready": false` until a champion has been promoted
for every configured horizon (exercise 9) — deliberately fails closed rather
than serving from a partial state. Once a champion exists for both
horizons, `/ready` returns 200 and `/metadata` lists each horizon's model
version and exact required feature columns (read from the model's own
MLflow signature, not a separately maintained schema). A real KServe
`InferenceService` on a live OpenShift AI cluster is out of scope for this
environment — see `deploy/` and `docs/pipeline_components.md`.

## 11. Inspect delayed monitoring and the retraining signal

```bash
python -m pytest tests/integration/test_monitor_delayed_signals.py -v
```

**Expected outcome:** three passing tests demonstrating (1) a monitoring
report naming the exact promoted champion version and a real rolling MAE
once a forecast has matured against a real observation; (2) the same report
with every delayed-performance section explicitly `null` before any
champion or matured prediction exists — not a crash, not a fabricated
number; (3) a monitoring run that reports feature drift never itself moves
the `champion` alias (drift is advisory only — see `docs/operations.md` and
ADR 0003).

## 12. Simulate drift and performance degradation

```bash
python -m pytest tests/unit/test_monitoring_drift.py tests/unit/test_monitoring_performance.py -v
```

**Expected outcome:** `test_synthetic_drift_fixture_creates_a_warning`
shows a deliberately shifted feature distribution crossing the drift
warning threshold. `test_performance_degradation_requests_retraining` shows
a rolling MAE genuinely worse than the champion's training-time persistence
baseline producing a `requested=true` retraining signal with a specific
reason string — while `test_good_performance_does_not_request_retraining`
and `test_too_few_matured_predictions_withholds_signal_even_if_degraded`
show the same machinery correctly staying silent when there's nothing
actionable yet.

## 13. Run the full quality gate yourself

```bash
make lint typecheck test notebook-check
```

**Expected outcome:** everything above, plus every other unit/contract/
integration test in the repository and a fresh-kernel execution of all six
notebooks, passes with no network access. This is exactly what
`.github/workflows/rivercast-ci.yaml` runs on every pull request.

---

## Live mode

Setting `mode: live` in a config (see `configs/base.yaml`'s `mode` field)
makes `components.fetch`/the source spike call the real PEGELONLINE REST
API instead of reading fixtures — the source adapter for this
(`rivercast.sources.pegelonline.PegelOnlineSource`) has existed since Phase
3 and needs no special setup beyond internet access.

**Current limitation:** `configs/openshift.yaml`, the config meant to pair
live PEGELONLINE access with persistent OpenShift storage, requires the S3
object-store backend — which is **not implemented yet**
(`rivercast.storage.object_store.create_object_store` raises for
`backend: s3`). Live mode today only works paired with the **local**
storage backend (data lands in your own `./artifacts/`, not shared/cluster
storage): copy `configs/local.yaml`, set `mode: live`, and rerun exercise 2
or `components.fetch` directly. A shared, persistent live deployment on
OpenShift AI needs the S3 backend implemented first — tracked as a
follow-up, not part of this phase.

## Resetting between attempts

```bash
bash scripts/reset_workshop.sh
```

Removes every locally-generated run, model, and promoted champion —
restoring "no champion set yet" for every horizon — without touching
fixtures, configs, source code, or committed reports. Safe to rerun.
