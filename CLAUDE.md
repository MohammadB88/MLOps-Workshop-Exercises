# CLAUDE.md

MLOps Workshop repository with hands-on exercises. Built with Zensical, deployed to GitHub Pages.

## Project Structure

```
MLOps-Workshop-Exercises/
├── .agents/skills/                    # Agent skill definitions
│   ├── ml-pipeline-workflow/
│   └── mlops-engineer/
├── .github/workflows/
│   ├── ci.yml                         # Zensical build + Pages deploy (active)
│   └── cd.yml                         # Old MkDocs workflow (disabled)
├── docs/                              # Zensical documentation
│   ├── index.md                       # Home page
│   ├── mlops-overview.md              # MLOps theory overview
│   ├── workshop-overview.md           # Workshop structure
│   ├── environment-requirements/     # Environment setup guides
│   │   ├── environment-requirement.md
│   │   ├── redhat-demo-environment.md
│   │   ├── mlflow-installation.md
│   │   ├── helm-installation.md
│   │   └── git-cheatsheet.md
│   ├── theory/introduction.md
│   ├── labs-docs/
│   │   ├── bike-demand-forecasting.md
│   │   ├── bike-demand-forecasting-pipeline.md
│   │   ├── wine-quality-classifier.md
│   │   ├── llm-instruction-tuning.md
│   │   ├── snippets/abbreviations.md
│   │   ├── tasks/                     # Task 1-9 guides
│   │   ├── 01_beginner/bike-forecasting/       # 9 step-by-step guides
│   │   ├── 02_intermediate/bike-demand-forecasting-pipeline/  # 6 step-by-step guides
│   │   ├── 02_intermediate/llm-instruction-tuning/  # 6 step-by-step guides
│   │   └── 03_advanced/
│   │       ├── kubeflow-advanced/     # 5 step-by-step guides
│   │       └── ml-security-compliance/ # 4 step-by-step guides
│   └── assets/                        # Images, CSS, JS

├── environment_preparations/
│   ├── helm_installtion.sh
│   ├── mlflow_installation.sh
│   ├── mlflow_odh_installation.sh     # OpenDataHub operator install (NEW)
│   └── mlflow_route.ymal              # Route YAML (note: typo in filename)
├── labs/
│   ├── 01_beginner/
│   │   ├── bike_demand_forecasting/
│   │   │   ├── notebooks/                 # 6 Jupyter notebooks
│   │   │   │   └── data/test_model/       # Test datasets
│   │   │   ├── models/                    # FastAPI + Containerfile + k8s
│   │   │   └── models_cors/               # CORS-enabled variant
│   │   └── wine_quality_TODO/             # Placeholder for next lab
│   ├── 02_intermediate/
│   │   ├── bike_demand_forecasting_pipeline/  # Kubeflow pipeline (742 lines)
│   │   │   ├── pipeline_bike_sharing.py       # 6 components
│   │   │   ├── serve.py                       # FastAPI serving
│   │   │   ├── Containerfile                  # ubi9/python-311
│   │   │   ├── requirements.txt
│   │   │   ├── test_process_dataset.py        # Unit test
│   │   │   ├── k8s/deployment.yaml            # Deployment + Service
│   │   │   └── data/                          # raw/, processed/, test_model/
│   │   ├── llm_instruction_tuning/
│   │   │   ├── Dockerfile
│   │   │   ├── environment.yml                # Conda env definition
│   │   │   ├── requirements.txt
│   │   │   ├── README.md
│   │   │   ├── data/                          # Training datasets
│   │   │   ├── models/                        # Merged model output
│   │   │   ├── notebooks/             # 6 Jupyter notebooks
│   │   │   ├── scripts/               # mlflow_register.py, test_client.py, build_and_push.sh
│   │   │   └── k8s/                   # deployment.yaml, service.yaml
│   │   └── archive/bike_demand_forecasting_pipeline/  # Old 4-component version
│   └── 03_advanced/
│       ├── kubeflow_advanced/
│       │   ├── README.md
│       │   ├── requirements.txt
│       │   ├── scripts/pipeline_helpers.py  # KFP component wrappers
│       │   └── notebooks/            # 5 notebooks
│       └── ml_security_compliance/
│           ├── README.md
│           ├── requirements.txt
│           ├── scripts/audit_logger.py  # JSONL audit trail
│           └── notebooks/            # 4 notebooks
├── zensical.toml                     # Zensical site config
├── zensical-test/                    # Zensical test configuration
├── requirements.txt                  # Root: zensical==0.0.43
├── LICENSE                           # MIT License
├── README.md                         # Project overview
├── ROADMAP.md                        # Enhancement roadmap
├── SECURITY.md                       # Security policy
├── skills-lock.json                  # Agent skill registry
└── repo_enahncements.txt             # AI agent prompts
```

## Common Commands

```bash
# Documentation
pip install -r requirements.txt
zensical serve              # Local dev (http://localhost:8000)
zensical build --clean      # Build site/
zensical gh-deploy --force  # Deploy to GitHub Pages

# Beginner Lab
cd labs/01_beginner/bike_demand_forecasting
pip install -r requirements.txt
jupyter lab

# Intermediate Pipeline
cd labs/02_intermediate/bike_demand_forecasting_pipeline
python test_process_dataset.py           # Run unit tests

# Intermediate LLMOps
cd labs/02_intermediate/llm_instruction_tuning
conda env create -f environment.yml
jupyter lab

# Advanced Labs
cd labs/03_advanced/kubeflow_advanced
cd labs/03_advanced/ml_security_compliance
```

## Key Technologies

- **Zensical**: Documentation framework (MkDocs Material theme migrated to Zensical)
- **MLflow**: Experiment tracking and model registry
- **Kubeflow Pipelines (KFP v2)**: Pipeline orchestration with `@dsl.component`/`@dsl.pipeline`
- **Evidently**: Model monitoring and drift detection (`DataDriftPreset`, `TargetDriftPreset`, `DataQualityPreset`)
- **FastAPI**: Model serving REST API with Pydantic validation
- **OpenShift/Kubernetes**: Container orchestration (UBI9 images)
- **scikit-learn**: ML framework (Random Forest)
- **Hugging Face Transformers & PEFT**: LLM fine-tuning (LoRA/QLoRA)
- **bitsandbytes**: Quantization for LLM training
- **vLLM**: Optimized LLM serving
- **cryptography**: Audit logging and compliance (advanced lab)

## Exercise Flows

### Bike Demand Forecasting (Beginner)

1. Data Exploration → Load UCI bike sharing dataset
2. Data Preparation → Clean, preprocess, split
3. Model Training → Train Random Forest with hyperparameter tuning, MLflow tracking
4. Model Registration → Register best model in MLflow
5. Model Testing → Test registered model via FastAPI endpoint
6. Model Monitoring → Set up Evidently for drift detection
7. Containerization → Containerfile + Kubernetes deployment
8. Deployment → Deploy and test on OpenShift

### Bike Demand Forecasting Pipeline (Intermediate)

Kubeflow pipeline (`pipeline_bike_sharing.py`) with 6 components:

1. `get_dataset` — Download and extract UCI dataset
2. `process_dataset` — Clean, rename columns, split into monthly CSVs, zip
3. `train_model` — Hyperparameter grid search (50-200 estimators, 5-20 depth), MLflow tracking
4. `register_model` — Find best run by RMSE, register in Model Registry, validate
5. `prepare_model_serving` — Download model from MLflow, package with serve.py + requirements + metadata
6. `monitor_model` — Evidently data drift, target drift, data quality reports (HTML + JSON)

Environment variables: `DATASET_URL`, `MLFLOW_REMOTE_TRACKING_SERVER`, `PARTICIPANT_FIRSTNAME`
Pipeline compiled with `compiler.Compiler().compile()`.

### LLMOps Instruction Tuning (Intermediate)

1. Setup & Exploration → Load base model (TinyLlama/Phi-2)
2. Data Preparation → Format instruction dataset, tokenize
3. LoRA Tuning → Train with LoRA/QLoRA, MLflow tracking
4. Evaluation → Perplexity, qualitative assessment
5. Versioning & Packaging → Register in MLflow (pytorch.log_model), merge weights, containerize
6. Deployment & Serving → Deploy to OpenShift/Kubernetes with vLLM

### LLMOps Model Persistence Chain

```
03 (train)  ──save──>  ./lora_adapter/          (local disk)
                │
04 (eval)   ──load──>  ./lora_adapter/
                │
05 (package) ─load──>  ./lora_adapter/
                │──log──>  MLflow (pytorch.log_model)
                │──save──>  ../models/merged_model
                │
Dockerfile   ──copy──>  models/merged_model
                │
06 (deploy)  ──test──>  http://localhost:8000
```

Note: `../models/merged_model` (from notebooks/) = `models/merged_model` (lab root), consumed by Dockerfile `COPY models/ /app/models/`.

### Kubeflow Advanced (Advanced)

- 01: Basic Triggers — KFP event-driven triggers
- 02: Advanced Workflows — Parallelism, conditionals, loops
- 03: Scheduling & Automation — Recurring runs, cron schedules
- 04: Optimization & Scaling — Resource tuning, distributed execution
- 05: Monitoring & Debugging — KFP UI, logging, troubleshooting

### ML Security & Compliance (Advanced)

- 01: Security Basics — Data encryption, access control, model poisoning
- 02: Governance Implementation — Model lineage, versioning policies
- 03: Audit Logging — JSONL audit trail, event querying
- 04: Compliance Reporting — Report generation, MLflow metadata

## Deployment Architecture

### Bike Forecasting (Beginner)
- **FastAPI** (`models/app.py`): REST API with CORS
- **Containerfile** (`models/Containerfile`): Python 3.11-slim
- **Kubernetes** (`models/k8s_deployment.yaml`): Deployment + Service
- **CORS variant** (`models_cors/`): Same with CORS middleware enabled

### Bike Forecasting Pipeline (Intermediate)
- **FastAPI** (`serve.py`): Loads model from local path, `/predict` + `/health` endpoints
- **Containerfile**: UBI9/python-311
- **Kubernetes** (`k8s/deployment.yaml`): Deployment (512Mi/250m requests, 1Gi/500m limits) + ClusterIP Service, liveness/readiness probes

### LLMOps
- **vLLM** (`models/vllm_server.py`): Optimized LLM serving
- **Dockerfile**: Container definition
- **Kubernetes** (`k8s/`): Deployment (16Gi mem, 4 CPU) + ClusterIP Service

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Trigger: push to `main`
- Steps: configure-pages → checkout → setup-python → `pip install zensical` → `zensical build --clean` → upload-pages-artifact → deploy-pages
- Permissions: `contents: read`, `pages: write`, `id-token: write`

## Important Notes

- Designed for Red Hat demo environment (OpenShift AI / OpenDataHub)
- MLflow tracking server: `http://mlflow-tracking.mlflow.svc.cluster.local:80`
- Participant names namespace experiments to avoid conflicts
- Pipeline base image: `quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703`
- Container serving base image: `registry.access.redhat.com/ubi9/python-311:latest`
- Beginner models directory was restructured: old `02_bike_demand_forecasting/` → `bike_demand_forecasting/`
- Old pipeline version preserved in `labs/02_intermediate/archive/`

## MLflow API Notes

- Use `MlflowClient().search_experiments()` instead of `mlflow.list_experiments()` (removed in newer versions)
- `mlflow.pytorch.log_model()` persists model weights; Hugging Face's `report_to="mlflow"` only logs metrics
- Retrieve best runs: `MlflowClient().search_runs(order_by=["metrics.rmse ASC"])`

## Coding Conventions

**KFP v2**: Components use `@dsl.component(base_image=..., packages_to_install=[...])` with `InputPath`/`OutputPath` type annotations. All components validate: file existence, non-empty data, expected columns, env vars set.

**MLflow**: `mlflow.set_tracking_uri()` / `mlflow.set_experiment()` pattern. Log with `log_param()`, `log_metric()`, `sklearn.log_model()`. Register with `register_model()`.

**FastAPI**: Pydantic `BaseModel` request schemas, `/predict` POST + `/health` GET endpoints, model loaded at startup.

**Evidently**: `Report(metrics=[DataDriftPreset(), TargetDriftPreset(), DataQualityPreset()])` then `report.run()` → `save_html()` + `as_dict()`.

**Audit Logging** (advanced): Custom `AuditLogger` class writing JSONL format with `log_event()` and `query_events()`.

**Naming**: Constants `UPPER_SNAKE_CASE`, functions `snake_case`, KFP components `verb_noun`, MLflow runs `RF_{n_estimators}_{max_depth}_{rand}`.
