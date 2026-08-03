# RiverCast pipeline components (Phase 8)

Ten single-purpose components under `components/`, each with a plain
`run(...)` function and a thin CLI `main()`. Every component is:

- callable directly as a Python function (from a notebook, a test, or a
  future KFP pipeline step);
- built from explicit typed parameters — no hidden global state;
- reading/writing large data through `rivercast.storage.ObjectStore` keys,
  never through KFP scalar outputs;
- returning a small, stable JSON envelope (`components.common.ComponentResult`);
- fail-closed: any contract violation returns `status="failed"` and the CLI
  (`components.common.emit`) exits non-zero.

## Component -> image mapping

| Component | Wraps | Image |
|---|---|---|
| `fetch` | `rivercast.ingest`, `rivercast.sources`, `rivercast.storage.RawArchive` | `rivercast-data` |
| `transform` | `rivercast.processing.{normalize,resample,features,labels,dataset}` | `rivercast-data` |
| `validate` | `rivercast.processing.quality` | `rivercast-data` |
| `train` | `rivercast.models.{split,baseline,train,evaluate,package,tracking}` | `rivercast-train` |
| `evaluate` | `rivercast.models.{package,evaluate}` (re-scores a saved artifact) | `rivercast-train` |
| `register` | `rivercast.models.registry.register_candidate` | `rivercast-train` |
| `promote` | `rivercast.models.registry` (gates + promotion transaction) | `rivercast-train` |
| `forecast` | champion lookup by alias + scoring | `rivercast-serving` |
| `deploy` | artifact loadability + prediction-sanity smoke test | `rivercast-serving` |
| `monitor` | freshness/coverage summary over a silver window | `rivercast-ops` |

The plan's finer-grained Phase 8 component list ("normalize", "feature
generation", "join labels", "smoke test") maps onto these ten: `transform`
folds normalize+resample+features+labels into one step (they share one
input, bronze, and gain nothing from separate container steps at this lab's
scale — plan §Phase 8: *"do not build one image for every five-line function
unless isolation is necessary"*), and the smoke-test step lives inside
`deploy`.

## Data flow

```text
fetch (per station)          -> bronze/
transform                    -> silver/hourly/ + gold/training/dataset_id=<id>/
validate                     -> reports/data_quality/
monitor                      -> reports/monitoring/
train                        -> models/local/<dataset_id>/ + an MLflow run
evaluate                     -> reports/evaluation/dataset_id=<id>/
register                     -> a new MLflow Model Registry version
promote                      -> challenger alias -> deploy validation -> champion alias
deploy                       -> loads a registered version, scores one row, checks it's finite
forecast                     -> loads the champion by run_id, scores one feature row
```

`tests/integration/test_components_end_to_end.py` runs every step above in
sequence against real (isolated, offline) object storage and MLflow tracking
— it is the executable specification of this data flow.

## What `forecast` and `deploy` intentionally do not do yet

Full prediction persistence (the Phase 9 prediction-record contract —
`prediction_id`, `dataset_id`, `input_snapshot_uri`, storage under the
`predictions` zone) and real KServe deployment (Phase 11) don't exist yet.
Building either ahead of the phase that owns it would be speculative:

- `forecast` produces one prediction record shaped exactly like the Phase 9
  schema and returns it in `ComponentResult.metadata`, but does not persist
  it or define `contracts/predictions.py` — that lineage/versioning contract
  and the scheduled/hourly calling context are Phase 9's job.
- `deploy` validates the one piece of deployment readiness that's available
  now: the registered artifact loads and produces a finite prediction. It
  does not create a KServe `InferenceService` or any cluster resource.

Both are still real, useful, independently testable components today, not
stubs that always return a canned answer.

## A real upstream bug found and worked around

Loading a registered model via `models:/<name>/<version>` (or
`models:/<name>@<alias>`) through `mlflow.pyfunc.load_model` /
`mlflow.sklearn.load_model` fails on Windows with mlflow 3.15:

```text
mlflow.exceptions.MlflowException: Could not find a registered artifact
repository for: c:. Currently registered schemes are: [...]
```

Root cause (traced through mlflow's own source): `mlflow.models.model.Model.load()`
re-passes an already-resolved native Windows path
(`C:\Users\...\model\MLmodel`) into a helper that expects a URI;
`urllib.parse.urlparse()` on that bare path misreads the drive letter `C:`
as a URI scheme. This reproduces from a two-line script with no RiverCast
code involved, so it is not something to route around by weakening our own
contracts — the practical fix is `components.common.model_run_uri()` /
`champion_run_uri()`, which resolve a model version's `run_id` first and
load via `runs:/<run_id>/model` instead, a code path that does not hit the
bug. Every component that loads a registered model (`deploy`, `forecast`)
goes through this helper.

A related, separate bug this phase also fixed: the first time a fresh
sqlite-backed MLflow experiment is created, MLflow defaults its artifact
store to `./mlruns/<experiment_id>` relative to the process's *current
working directory* rather than anywhere tied to the tracking database. Left
alone, this both pollutes the repository root and breaks test isolation
(two isolated tests would collide on the same shared `mlruns/`).
`rivercast.models.tracking._ensure_experiment` now creates the experiment
with an explicit `artifact_location` under `storage.root` whenever the
tracking store is a local sqlite/file backend (never overridden for a real
remote server).

## KFP compatibility (verified; full local execution not verifiable from this environment)

Every component's `run()` signature was verified to compile as a KFP
lightweight component (`@dsl.component`) and compile to pipeline YAML
(`kfp.compiler.Compiler().compile(...)`) without modification. Full
**execution** via `kfp.local.SubprocessRunner` could not be verified from
this Windows development environment: KFP's subprocess runner invokes the
interpreter through a POSIX shell (`sh -c ...`) and mis-resolves the
Windows-style venv interpreter path, a KFP/Windows incompatibility unrelated
to RiverCast's code (CLAUDE.md §Scope: agents are not expected to run inside
the trainee's — Linux — JupyterLab workbench; this reproduces even for a
two-line `add(a, b)` component with no RiverCast dependency at all).
`SubprocessRunner` execution should be re-verified in the actual OpenShift
AI JupyterLab workbench (Linux) as part of Phase 9, where the pipeline
`.ipynb` first submits real runs.

## Images

Four base images, each installing the package non-editable
(`pip install .`, no `[dev]` extras) and running as UID 1001 (non-root):

- `Containerfile.data` — `rivercast-data`
- `Containerfile.train` — `rivercast-train`
- `Containerfile.ops` — `rivercast-ops`
- `Containerfile.serving` — `rivercast-serving`

No Docker daemon is available in this development environment (or assumed
in the trainee's OpenShift AI workbench, CLAUDE.md rule 19), so an actual
image build was not performed here. Verified instead: staging exactly what
each `COPY` step stages (`pyproject.toml`, `src/`, `components/`,
`configs/`) into a clean directory and running `pip install .` followed by
each image's `ENTRYPOINT`/`CMD` (`python -m components.<name>.component
--help`) against a fresh venv — this exercises the same install and
entrypoint path the container build would, without requiring a container
runtime. All four image entrypoints resolved correctly. Real image builds
belong in CI or an approved cluster build service (CLAUDE.md rule 20;
plan §Phase 8 acceptance criteria).
