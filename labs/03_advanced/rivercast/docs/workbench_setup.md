# RiverCast workbench setup (OpenShift AI)

How to create the project-scoped JupyterLab workbench and initialize the
RiverCast lab from documented steps (PLAN.md Phase 1). No Docker daemon and no
cluster-admin rights are required inside the workbench.

## 1. Create the workbench

In the OpenShift AI dashboard, inside your data science project:

1. **Workbenches → Create workbench**
   - **Image:** Standard Data Science (Python 3.11, UBI9) — a supported,
     maintained image. A pinned custom image or the bootstrap script below
     locks the environment before workshop release.
   - **Deployment size:** Small (2 CPU / 8 Gi) is sufficient through Phase 7.
   - **Persistent storage:** create or attach a PVC (≥ 10 Gi), mounted at the
     default home directory. This is what makes repository files and the
     project environment survive workbench restarts.
2. **Data connection (S3):** attach the project's S3-compatible data
   connection. It injects `AWS_S3_ENDPOINT`, `AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION` — the variable names
   `configs/openshift.yaml` refers to. No credentials are ever written to
   config files or notebooks.
3. **Environment variable:** set `MLFLOW_TRACKING_URI` to the workshop MLflow
   service (e.g. `http://mlflow-tracking.mlflow.svc.cluster.local:80`).
4. **Pipeline access:** the project's default service account must be allowed
   to submit pipeline runs to the project's pipeline server (standard when a
   pipeline server is configured for the same data science project).

## 2. Initialize the project

Open the workbench, start a JupyterLab **Terminal**:

```bash
git clone <workshop-repository-url>
cd MLOps-Workshop-Exercises/labs/03_advanced/rivercast
bash scripts/bootstrap_workbench.sh
```

The bootstrap is idempotent and offline-safe after the first dependency
install: it creates `.venv/`, installs the pinned `rivercast` package in
editable mode, registers the **Python (rivercast)** Jupyter kernel, validates
`configs/local.yaml`, and runs the environment checks.

## 3. Verify

```bash
source .venv/bin/activate
rivercast --help
rivercast config validate --config configs/local.yaml
make lint typecheck test
```

Then open `notebooks/00_environment_check.ipynb`, select the
**Python (rivercast)** kernel, and use **Restart Kernel and Run All Cells**.
Expected at this phase: all core checks `PASS`; `WARN` for fixtures (arrive in
Phase 2), and for MLflow/KFP/cluster checks when the matching service is not
yet attached.

## 4. Restart behavior

Everything lives on the PVC-backed home directory: the clone, `.venv/`, the
kernel registration, and local artifacts under `artifacts/`. Stopping and
restarting the workbench must lose none of it — rerun step 3 after a restart
to confirm. If the verification fails after a restart, the storage was not
mounted persistently; fix the workbench storage before continuing.

## 5. Notes

- **No Docker inside the workbench** (CLAUDE.md rule 19): container images are
  built by CI or an approved cluster build service from Phase 8 onward.
- Fixture mode is the default (`configs/local.yaml`); live PEGELONLINE access
  is a deliberate opt-in (`mode: live`) — see `docs/workshop_exercises.md`
  ("Live mode") for how to enable it and its current storage-backend
  limitation.
