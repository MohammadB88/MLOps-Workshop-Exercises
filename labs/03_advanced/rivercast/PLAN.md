# RiverCast — Incremental Implementation Plan

**Goal:** Build a complete Level‑1 MLOps workshop use case that continuously collects river-gauge data, forecasts future water levels, evaluates predictions when the actual measurements arrive, retrains models automatically, promotes only validated candidates, and serves the champion model on OpenShift AI.

**Prepared:** 2 August 2026  
**Revision:** Jupyter-first development workflow  
**Primary audience:** Coding agents and maintainers of the MLOps Workshop repository

---

## 1. Brutally honest scope decision

Do **not** begin with DWD weather forecasts, Kafka, a feature store, multiple rivers, deep-learning models, or event-driven orchestration.

The difficult part is not training a regressor. It is building a trustworthy time-series loop without:

- timestamp and daylight-saving errors;
- data leakage;
- missing or revised sensor observations;
- irreproducible datasets;
- fake “continuous training”;
- deploying a candidate merely because training finished.

Build the gauge-only end-to-end loop first in an **OpenShift AI JupyterLab workbench**. Use notebooks to explore and verify each step interactively, but keep the reusable implementation in importable, tested Python modules. Add DWD observations after the loop works. Add ICON forecast grids only as an advanced extension.

RiverCast is an educational forecasting system, **not an official flood-warning product**. PEGELONLINE water level is relative to the local gauge zero; it is not the local river depth.

---

## 2. MVP definition

### 2.1 Prediction task

Predict the water level at **KAUB on the Rhine**:

- 6 hours ahead;
- 12 hours ahead.

Use an hourly canonical time grid.

### 2.2 Initial input stations

Start with a configurable Rhine corridor:

- MAINZ;
- OESTRICH;
- BINGEN;
- KAUB.

Resolve and store stations by immutable PEGELONLINE UUID, not by display name. The station list must live in configuration so it can be changed after the data-viability spike.

### 2.3 Initial features

Use only information available at forecast issue time:

- current and lagged water levels;
- rolling changes and rolling statistics;
- upstream gauge values and changes;
- hour, weekday, month;
- missingness indicators.

### 2.4 Initial models

1. Persistence baseline: `ŷ(t+h) = level(t)`.
2. Linear or ridge regression.
3. Scikit-learn `HistGradientBoostingRegressor` as the first serious candidate.

Do not use an LSTM or transformer in the MVP.

### 2.5 MVP success condition

The system is complete when it can:

1. ingest and archive new gauge measurements automatically;
2. create a versioned training dataset without leakage;
3. train and track candidates in MLflow;
4. compare candidates against persistence and the current champion;
5. register and promote only a passing candidate;
6. deploy the champion through a KServe-compatible endpoint;
7. issue scheduled forecasts and store prediction metadata;
8. join matured predictions with later observations;
9. calculate delayed model-quality metrics;
10. retrain on a schedule with conditional early exit;
11. run reproducibly in fixture mode without internet access.

---

## 2.6 Development environment: OpenShift AI JupyterLab

For this project, **local development** means development inside a project-scoped OpenShift AI workbench running JupyterLab. The browser is only the client; Python code executes in the workbench container on the OpenShift cluster.

Use the workbench for:

- cloning and editing the repository;
- exploratory data analysis;
- inspecting PEGELONLINE responses;
- designing and validating features;
- training baseline models interactively;
- calling MLflow and object storage;
- running unit and integration tests;
- executing Python components directly;
- compiling KFP pipelines;
- submitting and inspecting development pipeline runs.

Do not use notebooks as the production implementation. The required pattern is:

```text
Notebook
  └── imports rivercast Python package
        ├── source adapters
        ├── validation
        ├── feature engineering
        ├── training
        ├── evaluation
        └── pipeline components
```

A notebook may orchestrate functions and display results, but ingestion, transformation, training, evaluation, promotion, and serving logic must remain under `src/rivercast/`.

### Workbench constraints

A normal OpenShift AI workbench should not be assumed to have a Docker daemon or privileged container access. Therefore:

- run package code and tests directly in the workbench Python environment;
- use KFP `SubprocessRunner` for local component checks where compatible;
- build and scan container images in CI or an approved OpenShift build system;
- test the final immutable images through development pipeline runs;
- never require trainees to run Docker inside JupyterLab.

### Notebook quality gates

Each maintained notebook must:

- run from a fresh kernel with **Restart Kernel and Run All**;
- use repository-relative paths and configuration;
- import reusable code instead of duplicating it;
- avoid hidden state and manual cell-order dependencies;
- avoid embedded secrets;
- avoid committing large outputs;
- use fixture mode by default;
- be covered by an automated smoke execution in CI.

## 2.7 Note for coding agents

Build under maintainer review, the same as any other contribution. You are not expected to run inside a trainee's OpenShift AI workbench — that environment has no Node.js runtime or package-registry egress by design (§2.6). Do your work in whatever environment you're invoked from; trainees only see the finished notebooks, package, and pipelines once merged.

## 3. Target architecture

```text
┌───────────────────────────────────────────────────────────────┐
│ OpenShift AI JupyterLab workbench                            │
│                                                               │
│ Git clone → notebooks → imported Python modules → tests       │
│          → KFP component checks → compile/submit pipelines    │
└──────────────┬───────────────────────────────┬────────────────┘
               │                               │
               ▼                               ▼
       MLflow / object storage          Git repository / CI
                                               │
                                      builds immutable images
                                               │
                         PEGELONLINE           │
                              │                │
                              ▼                ▼
┌───────────────────────────────────────────────────────────────┐
│ Hourly data / operations pipeline                            │
│                                                               │
│ fetch → archive raw → normalize → validate → resample hourly │
│       → build latest features → invoke champion              │
│       → store forecasts → join matured labels                │
│       → calculate monitoring metrics                         │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
                 S3-compatible object storage
       bronze/  silver/  gold/  predictions/  reports/  models/
                           │
                 versioned dataset manifest
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│ Scheduled model pipeline                                      │
│                                                               │
│ check trigger → load dataset → validate → temporal split      │
│ → train baseline/candidate → evaluate → compare champion      │
│ → register challenger → conditional promotion → deploy       │
│ → endpoint smoke test → rollback on failure                   │
└───────────────┬───────────────────────────┬───────────────────┘
                │                           │
                ▼                           ▼
             MLflow                    KServe endpoint
      tracking + registry              champion model
                │                           │
                └─────────────┬─────────────┘
                              ▼
                   Evidently batch reports
```

### 3.1 Responsibilities

| Concern | Tool |
|---|---|
| Interactive development and workshop exercises | OpenShift AI JupyterLab workbench |
| Pipeline orchestration | OpenShift AI Pipelines / Kubeflow Pipelines v2 |
| Raw, curated, feature, prediction, and report artifacts | S3-compatible object storage |
| Experiment tracking and model registry | MLflow |
| Model serving | KServe; use a custom runtime if the cluster lacks a stable classical-ML runtime |
| Data and model evaluation reports | Evidently |
| Application API | FastAPI |
| Infrastructure metrics | Existing OpenShift monitoring / Prometheus |
| CI | Existing workshop CI platform, preferably GitHub Actions |
| Local querying | DuckDB or PyArrow over Parquet; do not add a database initially |

### 3.2 Two pipeline rule

Implement two primary KFP pipelines:

1. `rivercast-data-ops`
2. `rivercast-model`

Do not split every concern into a separate pipeline. Separate Python components are enough.

---

## 4. Repository layout

Add RiverCast as an isolated advanced lab under `labs/03_advanced/`, at the same level as `kubeflow_advanced/` and `ml_security_compliance/`. It keeps its own internal structure (package, pipelines, tests) rather than the lighter README+notebooks pattern used by the other labs — justified by its larger scope, not a convention this repo enforces elsewhere.

```text
labs/03_advanced/rivercast/
├── README.md
├── PLAN.md
├── CLAUDE.md
├── PROGRESS.md
├── pyproject.toml
├── Makefile
├── configs/
│   ├── base.yaml
│   ├── local.yaml
│   ├── openshift.yaml
│   └── stations.yaml
├── data_fixtures/
│   ├── pegelonline/
│   └── expected/
├── notebooks/
│   ├── 00_environment_check.ipynb
│   ├── 01_source_and_data_quality.ipynb
│   ├── 02_features_and_leakage.ipynb
│   ├── 03_baseline_training.ipynb
│   ├── 04_mlflow_tracking.ipynb
│   └── 05_pipeline_development.ipynb
├── src/rivercast/
│   ├── config.py
│   ├── contracts/
│   │   ├── raw.py
│   │   ├── hourly.py
│   │   ├── features.py
│   │   └── predictions.py
│   ├── sources/
│   │   ├── base.py
│   │   ├── pegelonline.py
│   │   └── fixture.py
│   ├── storage/
│   │   ├── object_store.py
│   │   ├── paths.py
│   │   └── manifests.py
│   ├── processing/
│   │   ├── normalize.py
│   │   ├── resample.py
│   │   ├── features.py
│   │   └── labels.py
│   ├── models/
│   │   ├── baseline.py
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   ├── promote.py
│   │   └── package.py
│   ├── monitoring/
│   │   ├── data_quality.py
│   │   ├── drift.py
│   │   └── performance.py
│   ├── serving/
│   │   ├── app.py
│   │   ├── schemas.py
│   │   └── predictor.py
│   └── cli.py
├── components/
│   ├── fetch/
│   ├── validate/
│   ├── transform/
│   ├── forecast/
│   ├── monitor/
│   ├── train/
│   ├── evaluate/
│   ├── register/
│   ├── promote/
│   └── deploy/
├── pipelines/
│   ├── data_ops_pipeline.py
│   ├── model_pipeline.py
│   └── compiled/
├── deploy/
│   ├── base/
│   ├── overlays/local/
│   └── overlays/openshift/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   └── smoke/
└── docs/
    ├── architecture.md
    ├── data_contract.md
    ├── model_card.md
    ├── operations.md
    └── workshop_exercises.md
```

Production logic must live under `src/`; notebooks import and demonstrate that logic but must not contain the only implementation. The notebooks are the primary interactive development and teaching interface.

---

## 5. Engineering rules for coding agents

These rules are duplicated as `CLAUDE.md` at the use-case root so a coding agent loads them automatically each session, without needing this whole document in context. Current phase status lives in `PROGRESS.md`; read it before starting work and update it as phases move between statuses. `CLAUDE.md` and `PROGRESS.md` govern maintainer-side, agent-assisted development only — see §2.7.

Apply these rules to every phase:

1. One phase per pull request.
2. Do not proceed until the phase acceptance criteria pass.
3. No network calls in unit tests.
4. All external calls require timeout, retry with backoff, and explicit error messages.
5. Every live data adapter must have a deterministic fixture adapter with the same output schema.
6. Store timestamps internally in UTC.
7. Preserve original source timestamps and offsets.
8. Never use future observations to construct features.
9. Never overwrite raw data.
10. Every dataset and model must be traceable to:
    - source window;
    - station UUIDs;
    - schema version;
    - feature version;
    - Git commit;
    - container image digest.
11. Use immutable image tags or digests in pipeline specs.
12. Keep thresholds and station selections in configuration.
13. Fail closed: invalid data must stop training and promotion.
14. A deployment failure must not move the `champion` alias.
15. Make fixture mode the default for workshops and CI.
16. Treat the JupyterLab workbench as the default developer environment.
17. Keep notebook cells thin: configuration, function calls, visualizations, and explanations.
18. A notebook is not accepted unless it passes a fresh-kernel run-all smoke test.
19. Do not assume Docker is available inside the workbench.
20. Compile pipeline YAML in the workbench, but build immutable images in CI or an approved cluster build service.
21. Every phase still ends in a pull request, but the maintainer runs all git operations themselves: branching, committing, pushing, and opening the PR. Agents leave changes uncommitted, summarize them, and stop — no self-merging, and only the maintainer marks a phase `done` in `PROGRESS.md`, after merging.

---

# Incremental build plan

## Phase 0 — Record scope and architecture decisions

### Build

Create short architecture decision records covering:

- target station and forecast horizons;
- hourly canonical frequency;
- gauge-only MVP;
- object-storage data layout;
- two-pipeline architecture;
- MLflow as tracker and registry;
- KServe-compatible serving;
- fixture mode;
- scheduled continuous training;
- explicit non-goals.

### Non-goals

- flood warnings;
- safety-critical decisions;
- nationwide forecasting;
- deep learning;
- Kafka;
- Feast;
- Spark;
- Airflow;
- DWD ICON data in the MVP;
- automatic deployment without validation.

### Acceptance criteria

- ADRs are committed.
- A single configuration file defines stations, horizons, time zone, storage paths, and thresholds.
- The README clearly labels RiverCast as educational.

### Deliverables

```text
docs/adr/0001-rivercast-scope.md
docs/adr/0002-data-versioning.md
docs/adr/0003-pipeline-boundaries.md
configs/base.yaml
```

---

## Phase 1 — Create the JupyterLab workbench and project skeleton

### Build

Create a project-scoped OpenShift AI workbench using a supported JupyterLab image and attach:

- persistent workbench storage;
- S3-compatible object-storage connection;
- MLflow connection or environment variables;
- the project service account required for development pipeline submission.

Inside JupyterLab:

1. clone the workshop repository using Git;
2. create the RiverCast Python package;
3. pin dependencies using the repository's existing convention;
4. install the package in editable mode;
5. add `pytest`, `ruff`, type checking, and notebook execution checks;
6. implement structured JSON logging;
7. implement typed configuration loading;
8. add local-filesystem storage implementing the same interface planned for S3;
9. create `00_environment_check.ipynb`.

Suggested terminal commands inside JupyterLab:

```bash
git clone <workshop-repository>
cd <workshop-repository>/labs/03_advanced/rivercast
python -m pip install -e ".[dev]"
make lint
make typecheck
make test
```

The environment notebook should verify:

- package imports;
- Git commit and Python version;
- writable persistent storage;
- object-store connectivity;
- MLflow connectivity;
- fixture access;
- KFP SDK availability;
- cluster API access needed to submit a development pipeline.

Start with a supported workbench image plus a locked project environment. Before the workshop is released, either build a pinned custom workbench image or provide a deterministic bootstrap script; do not rely on trainees installing an unbounded set of latest packages.

### Acceptance criteria

- A new workbench can clone and initialize the project from documented steps.
- `00_environment_check.ipynb` runs from a fresh kernel.
- `rivercast --help` works in the JupyterLab terminal.
- `rivercast config validate --config configs/local.yaml` succeeds.
- Unit tests and linting run inside the workbench.
- A deliberately invalid configuration fails with a useful message.
- Restarting the workbench does not lose repository files or required configuration.
- No Docker daemon is required inside the workbench.

### Deliverables

- documented workbench configuration;
- installable Python package;
- environment-check notebook;
- CI-ready test commands;
- configuration schema;
- local artifact directory;
- deterministic workbench bootstrap.


## Phase 2 — Run a data-viability spike

This phase is a gate. Do not build pipelines until the source is proven usable.

### Build

Create `01_source_and_data_quality.ipynb`, backed by a small reusable spike module or CLI, that:

1. lists Rhine stations from the stable PEGELONLINE REST API;
2. resolves configured station names to UUIDs;
3. fetches recent `W` measurements;
4. downloads a historical sample;
5. reports:
   - observation cadence;
   - missing intervals;
   - duplicates;
   - value ranges;
   - timestamp offsets;
   - overlap between stations;
   - usable history;
   - current source latency.

Use the stable REST API for live measurements. Treat HyDAS as evaluation-only while it remains beta.

### Questions the spike must answer

- Are all selected stations available for the same historical window?
- Is the nominal cadence consistently 15 minutes?
- Can data be parsed directly as JSON or CSV?
- Are timestamps ambiguous around DST transitions?
- Are there station metadata changes or long outages?
- Does upstream data improve a simple six-hour persistence baseline?
- Is KAUB still the best target for a manageable workshop dataset?

### Acceptance criteria

Produce `data_viability_report.md` with:

- final station UUIDs;
- exact source endpoints;
- chosen historical window;
- missingness table;
- data-quality risks;
- proceed/change/stop decision.

Proceed only when:

- at least two years of usable overlapping history can be assembled;
- the target has sufficient data for 6h and 12h labels;
- timestamps can be normalized deterministically;
- the source can be collected without credentials.

### Deliverables

```text
notebooks/01_source_and_data_quality.ipynb
scripts/source_spike.py
docs/data_viability_report.md
configs/stations.yaml
data_fixtures/pegelonline/
```

---

## Phase 3 — Implement source adapters and immutable raw storage

### Build

Define a source interface:

```python
class GaugeSource(Protocol):
    def list_stations(self, water: str) -> list[Station]: ...
    def fetch_measurements(
        self,
        station_uuid: str,
        parameter: str,
        start: datetime,
        end: datetime,
    ) -> list[Measurement]: ...
```

Implement:

- `PegelOnlineSource`;
- `FixtureGaugeSource`.

Add:

- request timeouts;
- retry with bounded exponential backoff;
- ETag / conditional request support where practical;
- response checksum;
- source metadata;
- idempotent writes.

### Raw layout

```text
bronze/
  source=pegelonline/
    parameter=W/
      station_uuid=<uuid>/
        event_date=YYYY-MM-DD/
          fetched_at=<utc-timestamp>-<checksum>.json
```

Never overwrite a raw response.

### Required raw metadata

```json
{
  "source": "pegelonline-rest-v2",
  "station_uuid": "...",
  "parameter": "W",
  "requested_start": "...",
  "requested_end": "...",
  "fetched_at_utc": "...",
  "http_status": 200,
  "etag": "...",
  "sha256": "...",
  "code_commit": "..."
}
```

### Acceptance criteria

- Re-running the same fetch does not duplicate normalized records.
- A simulated timeout retries and then fails cleanly.
- A malformed response is archived for diagnosis but not promoted downstream.
- Fixture and live adapters produce the same typed records.
- Unit tests make zero internet calls.

### Deliverables

- production source adapter;
- fixture adapter;
- raw storage implementation;
- source contract tests.

---

## Phase 4 — Build canonicalization and data-quality contracts

### Build

Normalize raw measurements to:

```text
station_uuid
station_name
water_body
parameter
observed_at_utc
source_offset
value
unit
quality_status
ingested_at_utc
source_sha256
schema_version
```

Then resample to an hourly grid.

Recommended hourly rule:

- use the last valid reading at or before the hour within an allowed tolerance;
- do not interpolate large gaps silently;
- emit missingness indicators;
- keep raw 15-minute data separately.

### Data-quality checks

- required columns;
- valid UUID;
- known parameter and unit;
- unique `(station_uuid, observed_at_utc, parameter)`;
- monotonic timestamps per station;
- plausible configured value bounds;
- maximum staleness;
- maximum short-gap missingness;
- station coverage;
- duplicate/conflict detection;
- DST regression tests.

A conflict is two different values for the same natural key. Store both raw observations, select using a documented rule, and flag the conflict.

### Acceptance criteria

- Spring-forward and fall-back test fixtures pass.
- The same raw inputs always create byte-equivalent canonical output.
- Invalid units or impossible timestamps stop the pipeline.
- Large gaps remain explicit; they are not filled by default.
- A data-quality summary is produced for every run.

### Deliverables

```text
silver/hourly/
reports/data_quality/
docs/data_contract.md
```

---

## Phase 5 — Build leakage-safe features and labels

### Build

Use `02_features_and_leakage.ipynb` to inspect feature behavior, while implementing feature generation under `src/rivercast/`. For each issue time `t`, create features from observations with timestamps `<= t`.

Example features:

```text
kaub_level_t
kaub_lag_1h
kaub_lag_3h
kaub_lag_6h
kaub_delta_1h
kaub_delta_6h
kaub_roll_mean_6h
kaub_roll_std_6h
bingen_level_t
bingen_delta_1h
oestrich_level_t
mainz_level_t
hour_sin
hour_cos
day_of_year_sin
day_of_year_cos
missing_<station>
```

Labels:

```text
target_level_6h  = KAUB level at t + 6h
target_level_12h = KAUB level at t + 12h
```

Use an explicit tolerance for matching future measurements to target time.

### Mandatory leakage tests

- Mutating observations after `t` must not change the feature row at `t`.
- Labels must not appear in feature columns.
- Fit preprocessing only on the training window.
- Rolling windows must end at `t`.
- Any future DWD forecast feature added later must be selected by forecast **issue time**, not only valid time.

### Dataset manifest

```json
{
  "dataset_id": "sha256:...",
  "created_at_utc": "...",
  "source_start_utc": "...",
  "source_end_utc": "...",
  "target_station_uuid": "...",
  "input_station_uuids": ["..."],
  "horizons_hours": [6, 12],
  "row_count": 0,
  "schema_version": "1",
  "feature_version": "1",
  "source_checksums": ["..."],
  "code_commit": "...",
  "image_digest": "..."
}
```

### Acceptance criteria

- Feature creation is deterministic.
- Leakage tests pass.
- Dataset ID changes when source data, features, or code changes.
- Rows with unavailable labels are excluded from training but retained for live forecasting.
- The generated dataset can be queried directly from Parquet.

### Deliverables

```text
notebooks/02_features_and_leakage.ipynb
gold/features/
gold/training/dataset_id=<id>/
docs/feature_spec.md
```

---

## Phase 6 — Establish baselines and offline evaluation

### Build

Create `03_baseline_training.ipynb` as the interactive training interface, backed entirely by reusable package functions. Expose the same workflow through a command line before MLflow or KFP:

```bash
rivercast train \
  --dataset-id <id> \
  --horizon 6 \
  --model hist-gradient-boosting
```

Use temporal evaluation:

- training: oldest interval;
- validation: following interval;
- test: newest untouched interval.

For a stronger implementation, add expanding-window backtesting after the simple split works.

### Metrics

Primary:

- MAE in centimeters;
- RMSE;
- MAE skill against persistence:

```text
skill = 1 - candidate_mae / persistence_mae
```

Slices:

- horizon;
- month or season;
- rising-water periods;
- falling-water periods;
- low-water and high-water quantiles;
- missing-upstream-feature cases.

Avoid MAPE because low or near-zero gauge values can make it unstable.

### Initial promotion policy

Configuration, not hard-coded values:

- candidate must beat persistence on the untouched test window;
- candidate must improve or remain within a strict tolerance of the champion;
- no critical slice may regress beyond its allowed threshold;
- artifact must pass serialization and inference-parity tests.

### Acceptance criteria

- A reproducible baseline report is committed.
- The model beats persistence for at least one configured horizon, or the report honestly concludes that it does not.
- Training twice with the same seed and data produces equivalent metrics.
- A deliberately leaked model is caught by tests or review fixtures.
- Model predictions before and after serialization match.

### Deliverables

```text
notebooks/03_baseline_training.ipynb
reports/baseline/
docs/model_card.md
models/local/
```

---

## Phase 7 — Add MLflow tracking and registry

### Build

Use `04_mlflow_tracking.ipynb` to demonstrate and verify experiment tracking, while keeping logging and registry operations in package code. For every training run, log:

- parameters;
- metrics;
- slice metrics;
- feature list;
- dataset manifest;
- data-quality report;
- evaluation plots;
- model signature;
- input example;
- Git commit;
- image digest;
- station UUIDs;
- horizon;
- serialized model.

Register passing training artifacts as versions of:

```text
rivercast-kaub-6h
rivercast-kaub-12h
```

Use aliases:

- `challenger`;
- `champion`.

Use tags such as:

```text
validation_status=pending|approved|rejected
dataset_id=<id>
horizon_hours=6
deployment_status=not_deployed|deployed|failed
```

### Promotion transaction rule

1. Register candidate.
2. Assign `challenger`.
3. Validate deployable artifact.
4. Deploy candidate to a non-production endpoint or revision.
5. Run smoke tests.
6. Only then move `champion`.
7. Retain previous champion metadata for rollback.

Do not update `champion` before deployment validation succeeds.

### Acceptance criteria

- Every model version links to its originating run and dataset.
- The champion can be loaded by alias.
- A rejected candidate remains traceable but never receives `champion`.
- Registry tests cover first-model bootstrap when no champion exists.
- Promotion is idempotent.

### Deliverables

- MLflow integration;
- registry workflow;
- promotion policy tests;
- model-card template;
- `notebooks/04_mlflow_tracking.ipynb`.

---

## Phase 8 — Containerize reusable pipeline components

### Build

Create small, single-purpose container entry points for:

- fetch;
- normalize;
- validate;
- feature generation;
- forecast;
- join labels;
- monitor;
- train;
- evaluate;
- register;
- promote;
- deploy;
- smoke test.

Prefer a small number of shared base images:

```text
rivercast-data:<git-sha>
rivercast-train:<git-sha>
rivercast-ops:<git-sha>
rivercast-serving:<git-sha>
```

Do not build one image for every five-line function unless isolation is necessary.

### Component contract

Every component must:

- be callable first as a normal Python function from JupyterLab;
- be testable with KFP local execution using `SubprocessRunner` where supported;
- accept explicit typed parameters;
- read large data through object-store URIs, not KFP scalar outputs;
- emit a small JSON result and artifact URI;
- log run ID and dataset ID;
- exit non-zero on contract failure;
- be executable locally.

### Acceptance criteria

- Every component runs against fixtures directly inside the workbench.
- Supported components pass KFP `SubprocessRunner` checks in the workbench.
- Final container behavior is tested by CI and a development pipeline run, not by assuming Docker-in-Docker in JupyterLab.
- Images run as non-root.
- Image builds are reproducible and vulnerability-scanned by the existing platform.
- Pipeline code references immutable tags or digests.
- Component outputs are small and stable.

### Deliverables

```text
components/
Containerfile.data
Containerfile.train
Containerfile.ops
Containerfile.serving
```

---

## Phase 9 — Implement `rivercast-data-ops` pipeline

Develop the pipeline from `05_pipeline_development.ipynb` by importing component and pipeline definitions from `pipelines/`. The notebook may compile, submit, and inspect runs, but the authoritative pipeline definition remains version-controlled Python code.

Development loop:

```text
run component function in notebook
    → run tests
    → run compatible component with KFP SubprocessRunner
    → compile pipeline YAML
    → submit development run from workbench
    → inspect artifacts and logs
```

### Pipeline graph

```text
resolve-config
      │
      ▼
fetch-live-measurements
      │
      ▼
archive-and-normalize
      │
      ▼
validate-and-resample-hourly
      │
      ├───────────────┐
      ▼               ▼
build-latest-features update-training-dataset
      │               │
      ▼               ▼
load-champion       join-matured-predictions
      │               │
      ▼               ▼
issue-6h/12h        calculate-delayed-metrics
forecasts             │
      │               ▼
      └──────────► monitoring-report
```

### Schedule

Run hourly. If source data is not fresh enough:

- do not issue a forecast;
- record a failed freshness check;
- keep the last deployed model unchanged;
- do not fabricate input values.

Disable KFP caching for live-fetch, forecast, label-join, and monitoring steps. Caching may remain enabled for deterministic transformations keyed by immutable inputs.

### Prediction record

```json
{
  "prediction_id": "...",
  "issued_at_utc": "...",
  "target_time_utc": "...",
  "horizon_hours": 6,
  "target_station_uuid": "...",
  "prediction_cm": 0.0,
  "model_name": "rivercast-kaub-6h",
  "model_version": "17",
  "model_alias": "champion",
  "dataset_id": "...",
  "feature_version": "1",
  "input_snapshot_uri": "...",
  "created_by_pipeline_run": "..."
}
```

### Acceptance criteria

- The pipeline compiles to KFP YAML.
- It runs end-to-end in fixture mode.
- Two identical raw fetches do not duplicate canonical observations.
- A stale-source fixture prevents forecast generation.
- Matured predictions receive actual values and errors.
- Pipeline artifacts and logs are visible in OpenShift AI.
- An hourly recurring run can be created and removed reproducibly.

### Deliverables

```text
notebooks/05_pipeline_development.ipynb
pipelines/data_ops_pipeline.py
pipelines/compiled/rivercast-data-ops.yaml
tests/integration/test_data_ops_pipeline.py
```

---

## Phase 10 — Implement `rivercast-model` pipeline

### Pipeline graph

```text
resolve-config
      │
      ▼
check-training-trigger
      │
      ├── no trigger ──► record skipped run
      │
      ▼
materialize-dataset-version
      │
      ▼
validate-training-data
      │
      ▼
temporal-split
      │
      ├──────────────┐
      ▼              ▼
train-persistence  train-candidate
      │              │
      └──────┬───────┘
             ▼
      evaluate-and-slice
             │
             ▼
      load-current-champion
             │
             ▼
      apply-promotion-gates
        │              │
   rejected         approved
        │              │
        ▼              ▼
 record result      register challenger
                       │
                       ▼
                 deploy candidate
                       │
                       ▼
                   smoke test
                  │          │
                fail        pass
                  │          │
                  ▼          ▼
              rollback    move champion
```

### Trigger logic

Run on a fixed schedule, initially weekly. Exit successfully without training when:

- fewer than `min_new_labeled_rows` are available;
- data quality fails;
- a training run for the same dataset ID already exists.

Later, the schedule can run daily while the conditional gate controls actual training.

This is simpler and more reliable than implementing cross-pipeline event triggers in the first version.

### Deployment smoke tests

- endpoint becomes ready;
- health endpoint succeeds;
- model version reported by endpoint is expected;
- fixed request schema is accepted;
- prediction is finite and plausible;
- local artifact and served endpoint predictions match within tolerance;
- previous endpoint remains available until validation completes.

### Acceptance criteria

Test four scenarios:

1. No new data → pipeline skips.
2. Candidate worse than champion → registered/rejected, no deployment.
3. Candidate better but deployment fails → champion unchanged.
4. Candidate passes and endpoint works → champion changes.

### Deliverables

```text
pipelines/model_pipeline.py
pipelines/compiled/rivercast-model.yaml
tests/integration/test_model_pipeline.py
```

---

## Phase 11 — Build the serving layer

### Build

Implement a FastAPI service with:

```text
GET  /health
GET  /ready
GET  /metadata
POST /predict
```

Example request:

```json
{
  "issue_time": "2026-08-02T15:00:00Z",
  "horizon_hours": 6,
  "features": {
    "kaub_level_t": 100.0,
    "bingen_level_t": 120.0
  }
}
```

Example response:

```json
{
  "target_station": "KAUB",
  "horizon_hours": 6,
  "target_time": "2026-08-02T21:00:00Z",
  "prediction_cm": 96.4,
  "model_name": "rivercast-kaub-6h",
  "model_version": "17",
  "dataset_id": "sha256:...",
  "feature_version": "1"
}
```

### Deployment strategy

Preferred order:

1. Use an existing stable KServe runtime that supports the chosen model format.
2. Otherwise deploy `rivercast-serving` as a custom KServe `ServingRuntime`.
3. Keep direct FastAPI-on-OpenShift deployment as a local/development fallback.

Do not make the project dependent on a technology-preview runtime.

### Important design rule

The service must not independently recreate training features using different code. Reuse the same feature contract/package or accept a feature vector produced by the data pipeline.

For the workshop application, add a higher-level endpoint that fetches the latest validated feature snapshot and calls the model endpoint. Keep that orchestration outside the model runtime.

### Acceptance criteria

- Local Docker smoke test passes.
- KServe endpoint returns model metadata.
- Invalid horizon or missing features returns a clear 4xx response.
- Old and new model revisions can be tested independently.
- Rollback manifest restores the prior model.

### Deliverables

```text
src/rivercast/serving/
deploy/base/inferenceservice.yaml
deploy/base/servingruntime.yaml  # only if required
tests/smoke/test_serving.py
```

---

## Phase 12 — Implement delayed monitoring and retraining signals

### Build

Run monitoring as part of the data-operations pipeline after sufficient records accumulate.

#### Data monitoring

- source freshness;
- row count;
- missingness;
- duplicate/conflict count;
- station coverage;
- feature range;
- feature drift;
- prediction drift.

#### Delayed model monitoring

After actual water levels arrive:

- MAE and RMSE by horizon;
- rolling seven-day and thirty-day metrics;
- error relative to persistence;
- rising/falling-water slices;
- error by model version;
- prediction latency and endpoint failures.

Use Evidently for batch reports. Store raw predictions and observations in the workshop object store; store monitoring summaries separately.

### Retraining signal

Create a small retraining decision artifact:

```json
{
  "requested": true,
  "reasons": [
    "minimum_new_labels_reached",
    "rolling_mae_degraded"
  ],
  "reference_model_version": "17",
  "new_labeled_rows": 240,
  "created_at_utc": "..."
}
```

The scheduled model pipeline reads this signal but still re-runs all data and model gates.

Do not retrain solely because feature drift is detected. Drift is a trigger to investigate or evaluate; it is not proof that a new model will be better.

### Acceptance criteria

- Reports work with no labels and with delayed labels.
- A synthetic drift fixture creates a warning.
- A performance-degradation fixture creates a retraining request.
- A drift-only fixture does not bypass promotion gates.
- Reports identify the exact model version and data window.

### Deliverables

```text
reports/evidently/
src/rivercast/monitoring/
docs/operations.md
```

---

## Phase 13 — Add CI and release automation

### Pull-request checks

- formatting and linting;
- type checks;
- unit tests;
- contract tests;
- fixture integration tests;
- fresh-kernel notebook smoke execution;
- leakage tests;
- pipeline compilation;
- Kubernetes manifest validation;
- container build;
- dependency and image scanning, using existing workshop tooling.

### Main-branch workflow

1. Build immutable images.
2. Push images.
3. Compile pipeline YAML with exact image digests.
4. publish pipeline definitions as release artifacts;
5. run fixture-mode end-to-end smoke test;
6. optionally upload a new pipeline version to the development OpenShift project.

Do not automatically deploy a newly trained production model merely because application code merged. Code CI and model promotion are separate controls.

### Release metadata

```text
git_commit
release_version
image_digests
pipeline_spec_checksums
schema_version
feature_version
compatible_workshop_version
```

### Acceptance criteria

- A broken data contract fails CI.
- A changed feature schema requires a feature-version change.
- Compiled pipeline YAML contains immutable images.
- CI never requires live PEGELONLINE access.
- A tagged release includes fixture data, manifests, and compiled pipelines.

### Deliverables

```text
.github/workflows/rivercast-ci.yaml
.github/workflows/rivercast-release.yaml
```

Adapt filenames to the repository's existing CI system.

---

## Phase 14 — Integrate with the workshop learning flow

### Suggested trainee sequence

1. Start the OpenShift AI workbench and run `00_environment_check.ipynb`.
2. Explore source data and an injected sensor failure in `01_source_and_data_quality.ipynb`.
3. Inspect leakage-safe features in `02_features_and_leakage.ipynb`.
4. Train persistence and candidate models in `03_baseline_training.ipynb`.
5. Compare MLflow runs in `04_mlflow_tracking.ipynb`.
6. Test component functions and compile the pipeline in `05_pipeline_development.ipynb`.
7. Submit the data pipeline in fixture mode from JupyterLab.
8. Run the model pipeline with a deliberately rejected candidate.
9. Modify a legitimate model parameter or dataset window.
10. Observe successful candidate promotion.
11. Call the KServe endpoint.
12. Inspect delayed monitoring reports.
13. Simulate drift or missing data and observe the system response.

### Provide two modes

#### Instructor / CI mode

- deterministic fixtures;
- prebuilt images;
- short data window;
- predictable pass/fail outcomes.

#### Live mode

- PEGELONLINE REST API;
- recent measurements;
- persistent object storage;
- scheduled pipeline runs.

The workshop must remain fully usable when PEGELONLINE is unavailable.

### Documentation to add

- theory: automated data and model pipelines;
- time-series leakage;
- delayed labels;
- champion/challenger;
- data and model validation;
- monitoring with delayed ground truth;
- scheduled continuous training;
- operational limitations.

### Acceptance criteria

- A trainee can complete the lab from the OpenShift AI JupyterLab workbench without external credentials.
- Every exercise has an expected observable outcome.
- Failure exercises are reversible.
- Instructor reset scripts remove runs and restore champion state.
- The lab does not require editing cluster-wide resources.
- All notebooks run successfully from fresh kernels and import the same code used by pipelines.

### Deliverables

```text
docs/workshop_exercises.md
docs/instructor_guide.md
scripts/reset_workshop.sh
```

---

## Phase 15 — Harden before calling it complete

### Reliability

- idempotent ingestion;
- bounded retries;
- source timeout;
- partial-run recovery;
- duplicate-run protection;
- pipeline concurrency policy;
- object-store lifecycle policy;
- retention policy for raw and prediction data.

### Security

- non-root containers;
- read-only filesystem where possible;
- OpenShift Secrets for credentials;
- scoped service accounts;
- least-privilege object-store access;
- endpoint authentication appropriate to the workshop;
- no secrets in notebooks, manifests, or MLflow tags.

### Reproducibility

- pinned dependencies;
- immutable images;
- source checksums;
- dataset manifests;
- seeded training;
- pipeline versions;
- model signatures;
- artifact retention.

### Operational tests

- PEGELONLINE unavailable;
- one station stale;
- malformed measurement;
- object store temporarily unavailable;
- MLflow unavailable;
- no current champion;
- deployment readiness timeout;
- candidate endpoint returns invalid output;
- DST transition;
- repeated scheduled run;
- pipeline cancellation and rerun.

### Acceptance criteria

- A runbook documents each failure.
- Previous champion remains available during model-pipeline failures.
- All core workflows have fixture-based integration tests.
- The system can be reset to a known state.
- The architecture diagram matches the implementation.

---

# Extension phases

## Extension A — Add DWD weather observations

Add only after gauge-only MVP completion.

### Inputs

- recent precipitation;
- temperature;
- humidity;
- optionally RADOLAN-derived rainfall aggregates.

### Requirements

- map weather stations or radar cells to the relevant river corridor/catchment;
- archive source data;
- normalize timestamps to UTC;
- add feature-version `2`;
- compare against the gauge-only champion;
- deploy only if the candidate passes the same gates.

The gauge-only model remains a required fallback.

---

## Extension B — Add DWD ICON-D2 forecasts

This is an advanced data-engineering exercise.

### Risks

- GRIB2 processing;
- large files;
- spatial extraction;
- forecast-run/version handling;
- issue-time versus valid-time leakage;
- changing forecast availability.

### Mandatory model-table keys

```text
forecast_issued_at_utc
forecast_valid_at_utc
lead_time_hours
model_run
grid_cell
parameter
value
```

At issue time `t`, the feature builder may only use a forecast whose `forecast_issued_at_utc <= t`.

Do not use a reanalysis or later forecast run as though it were available at historical prediction time.

---

## Extension C — Multi-station models

Possible progression:

1. one model per target station and horizon;
2. shared feature code;
3. shared training pipeline with a loop;
4. optional global station model.

Do not begin with a global model. It complicates station identity, calibration, and slice evaluation.

---

## Extension D — Canary rollout

After direct replacement works reliably:

- deploy candidate revision;
- route a limited share of non-critical workshop traffic;
- compare service health;
- promote or roll back.

For scheduled forecasts, shadow evaluation is often clearer than traffic splitting because true labels arrive later.

---

# Definition of done

RiverCast is Level‑1 complete only when all boxes are checked:

## Data

- [ ] Live PEGELONLINE ingestion is scheduled.
- [ ] Fixture ingestion is deterministic.
- [ ] Raw responses are immutable.
- [ ] Canonical data is versioned.
- [ ] Data-quality checks block invalid datasets.
- [ ] Feature/label generation is leakage-tested.
- [ ] Dataset manifests provide lineage.

## Model

- [ ] Persistence baseline exists.
- [ ] Temporal evaluation is automated.
- [ ] Runs and artifacts are logged in MLflow.
- [ ] Candidate and champion comparison is automated.
- [ ] Rejected candidates are retained but not deployed.
- [ ] Model alias changes only after deployment smoke tests.

## Serving

- [ ] Champion model is available through a KServe-compatible endpoint.
- [ ] Endpoint exposes model metadata.
- [ ] Rollback is tested.
- [ ] Serving and offline inference are parity-tested.

## Operations

- [ ] Scheduled forecasts are stored with model version and target time.
- [ ] Actual values are joined when they arrive.
- [ ] Delayed performance metrics are automated.
- [ ] Drift and data-freshness reports are automated.
- [ ] Retraining is scheduled and conditionally skipped.
- [ ] Promotion gates remain mandatory after a retraining trigger.

## Engineering

- [ ] Components run directly in the JupyterLab workbench and in KFP.
- [ ] Maintained notebooks pass fresh-kernel smoke execution.
- [ ] CI compiles pipelines and tests fixtures.
- [ ] Images and pipeline specs are immutable.
- [ ] Secrets are externalized.
- [ ] Failure runbooks exist.
- [ ] The full workshop works without internet access.
- [ ] No workshop step requires Docker inside the JupyterLab workbench.

---

# Recommended implementation order

Do not reorder this list:

```text
1. Scope and ADRs
2. OpenShift AI JupyterLab workbench and project skeleton
3. Notebook-driven data viability spike
4. Source adapter and immutable raw storage
5. Canonical data and quality contracts
6. Leakage-safe features and labels
7. Baseline and offline evaluation
8. MLflow tracking and registry
9. Containerized components
10. Data-operations pipeline
11. Model pipeline
12. Serving
13. Monitoring and retraining signals
14. CI/release automation
15. Workshop integration
16. Hardening
17. DWD observations
18. ICON-D2 forecasts
```

The first demonstrable vertical slice should be:

```text
JupyterLab workbench + fixture data
  → imported package functions
  → canonical hourly dataset
  → persistence + candidate training
  → MLflow registration
  → workbench-hosted FastAPI smoke prediction
```

The second vertical slice should be:

```text
live PEGELONLINE
  → scheduled data pipeline
  → stored forecast
  → delayed label join
  → monitoring report
```

The third vertical slice should be:

```text
scheduled training
  → candidate/champion gates
  → KServe deployment
  → smoke test
  → promotion or rollback
```

---

# Official references used for the plan

- [MLOps for All — Level 1: Automated ML Pipeline](https://mlops-for-all.github.io/en/docs/introduction/levels/)
- [PEGELONLINE REST API User's Guide](https://m.pegelonline.wsv.de/webservice/guideRestapi)
- [PEGELONLINE downloads and historical data](https://www.pegelonline.wsv.de/webservice/downloads)
- [PEGELONLINE help: historical formats, timestamps, water-level meaning, and update frequency](https://www.pegelonline.wsv.de/gast/hilfe)
- [DWD Open Data](https://www.dwd.de/EN/ourservices/opendata/opendata.html)
- [DWD Climate Data Center](https://www.dwd.de/EN/ourservices/cdc/cdc.html)
- [DWD numerical forecast data](https://www.dwd.de/EN/ourservices/nwp_forecast_data/nwp_forecast_data.html)
- [Red Hat OpenShift AI — Creating a workbench and using notebooks](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/openshift_ai_tutorial_-_fraud_detection_example/creating-a-workbench-and-using-notebooks)
- [Red Hat OpenShift AI — Working in JupyterLab](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_in_your_data_science_ide/working_in_jupyterlab)
- [Red Hat OpenShift AI — Implementing pipelines from JupyterLab](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/openshift_ai_tutorial_-_fraud_detection_example/implementing-pipelines)
- [Red Hat OpenShift AI — Working with AI pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_with_ai_pipelines)
- [Red Hat OpenShift AI — Deploying models](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/deploying_models)
- [Kubeflow Pipelines — Core functions](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/)
- [Kubeflow Pipelines — Execute pipelines locally](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/execute-kfp-pipelines-locally/)
- [Kubeflow Pipelines — Execute pipelines locally](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/execute-kfp-pipelines-locally/)
- [MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/)
- [KServe — Deploying MLflow models](https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/mlflow)
- [KServe — ServingRuntime](https://kserve.github.io/website/docs/concepts/resources/servingruntime)
- [Evidently — Monitoring overview](https://docs.evidentlyai.com/docs/platform/monitoring_overview)
- [Evidently — Regression evaluation](https://docs.evidentlyai.com/metrics/preset_regression)
- [Evidently — Data drift](https://docs.evidentlyai.com/metrics/preset_data_drift)
