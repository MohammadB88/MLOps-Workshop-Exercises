# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MLOps Workshop repository containing hands-on exercises for learning MLOps concepts. The workshop materials are built with MkDocs and published to GitHub Pages at https://mohammadb88.github.io/MLOps-Workshop-Exercises/.

The workshop is organized into **three progressive skill levels**:
- **Beginner**: Wine Quality Classifier and Bike Demand Forecasting basics
- **Intermediate**: End-to-end pipelines with Kubeflow
- **Advanced**: CI/CD and monitoring (planned)

## Common Commands

### Documentation (MkDocs)

```bash
# Install dependencies
pip install -r requirements.txt

# Serve documentation locally (for development)
mkdocs serve

# Build documentation
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy --force
```

### Lab Materials

The lab materials are organized by skill level under `labs/`:

```bash
# Beginner labs
cd labs/01_beginner/02_bike_demand_forecasting
pip install -r requirements.txt

# Intermediate labs
cd labs/02_intermediate/01_bike_demand_forecasting_pipeline
pip install -r requirements.txt
```

### Running Jupyter Notebooks

The workshop uses Jupyter notebooks for hands-on exercises. Navigate to the appropriate directory and start Jupyter:

```bash
cd labs/01_beginner/02_bike_demand_forecasting
jupyter notebook
# or
jupyter lab
```

## Architecture

### Repository Structure

```
MLOps-Workshop-Exercises/
├── README.md                          # Project introduction and overview
├── ROADMAP.md                         # Project roadmap and future plans
├── LICENSE                            # MIT License
├── SECURITY.md                       # Security policy
├── mkdocs.yml                         # MkDocs configuration
├── requirements.txt                   # Documentation dependencies
├── docs/
│   ├── index.md                       # Landing page
│   ├── mlops-overview.md              # MLOps concepts
│   ├── workshop-overview.md           # Lab overview
│   ├── environment-requirement.md     # Prerequisites
│   ├── theory/                        # Learning materials (planned)
│   │   └── introduction.md
│   ├── labs-docs/                     # Lab documentation
│   │   ├── wine-quality-classifier.md
│   │   ├── bike-demand-forecasting.md
│   │   ├── bike-forecasting/         # Step-by-step guides
│   │   ├── llm-instruction-tuning.md  # LLMOps exercise overview
│   │   ├── llm-instruction-tuning/    # LLMOps step-by-step guides
│   │   │   ├── 01_setup_exploration.md
│   │   │   ├── 02_data_preparation.md
│   │   │   ├── 03_lora_tuning.md
│   │   │   ├── 04_evaluation.md
│   │   │   ├── 05_versioning_packaging.md
│   │   │   └── 06_deployment_serving.md
│   │   └── tasks/                     # Task descriptions for automation exercises
│   └── assets/                        # Images, CSS, JS, HTML overrides
├── labs/                              # Hands-on lab materials
│   ├── 01_beginner/
│   │   └── 02_bike_demand_forecasting/
│   │       ├── 01_data_exploration.ipynb
│   │       ├── 02_data_preparation.ipynb
│   │       ├── 03_model_training.ipynb
│   │       ├── 04_model_registeration.ipynb
│   │       ├── 05_model_testing_endpoint.ipynb
│   │       ├── 06_model_monitoring.ipynb
│   │       ├── data/
│   │       ├── models/
│   │       └── requirements.txt
│   └── 02_intermediate/
│       ├── 01_bike_demand_forecasting_pipeline/
│       │   ├── pipeline_bike_sharing.py
│       │   ├── data/
│       │   └── requirements.txt
│       └── 02_llm_instruction_tuning/
│           ├── notebooks/
│           │   ├── 01_setup_exploration.ipynb
│           │   ├── 02_data_preparation.ipynb
│           │   ├── 03_lora_tuning.ipynb
│           │   ├── 04_evaluation.ipynb
│           │   ├── 05_versioning_packaging.ipynb
│           │   └── 06_deployment_serving.ipynb
│           ├── scripts/
│           │   ├── prepare_data.py
│           │   ├── train_lora.py
│           │   ├── evaluate.py
│           │   ├── build_and_push.sh
│           │   ├── mlflow_register.py
│           │   └── test_client.py
│           ├── k8s/                   # Kubernetes deployment manifests
│           │   ├── deployment.yaml
│           │   └── service.yaml
│           ├── data/                  # Processed datasets (gitignored)
│           ├── models/                # Model outputs (gitignored)
│           ├── requirements.txt       # Python dependencies
│           ├── README.md              # Lab-specific overview
│           └── environment.yml        # Conda environment (optional)
└── sample-mkdocs/                    # MkDocs examples
```

### Documentation Structure

The documentation is organized under `docs/`:

- `docs/index.md` - Landing page with workshop introduction
- `docs/mlops-overview.md` - MLOps concepts and principles
- `docs/workshop-overview.md` - Overview of hands-on labs
- `docs/environment-requirement.md` - Prerequisites and setup
- `docs/theory/` - Learning materials and theory (planned expansion)
- `docs/labs-docs/` - Detailed lab documentation
  - `wine-quality-classifier.md` - Beginner exercise
  - `bike-demand-forecasting.md` - Main exercise overview
  - `bike-forecasting/` - Step-by-step guides (9 steps)
  - `llm-instruction-tuning.md` - LLMOps exercise overview
  - `llm-instruction-tuning/` - LLMOps step-by-step guides
    - `01_setup_exploration.md`
    - `02_data_preparation.md`
    - `03_lora_tuning.md`
    - `04_evaluation.md`
    - `05_versioning_packaging.md`
    - `06_deployment_serving.md`
  - `tasks/` - Task descriptions for automation exercises
- `docs/assets/` - Images, CSS, JavaScript, and HTML overrides

### Lab Materials Structure

The labs are organized by skill level:

**Beginner Labs** (`labs/01_beginner/`):
- `02_bike_demand_forecasting/` - Main exercise with 6 notebooks covering the full MLOps lifecycle

**Intermediate Labs** (`labs/02_intermediate/`):
- `01_bike_demand_forecasting_pipeline/` - Kubeflow pipeline automation
- `02_llm_instruction_tuning/` - LLMOps exercise focusing on instruction tuning small LLMs

### LLMOps Workshop Exercise

The LLMOps workshop exercise extends MLOps concepts to large language model systems, specifically instruction tuning workflows. This intermediate-level exercise covers:

* Parameter-efficient fine-tuning with LoRA/QLoRA
* Experiment tracking with MLflow
* Model evaluation and versioning
* Containerization and Kubernetes-native deployment
* LLM serving lifecycle management

Exercise materials are located in `labs/02_intermediate/02_llm_instruction_tuning/` and include:
* Jupyter notebooks for hands-on exercises
* Helper scripts for data preparation, training, and deployment
* Documentation in `docs/labs-docs/02_intermediate/llm-instruction-tuning/`

Key technologies used:
* Hugging Face Transformers and PEFT for model tuning
* bitsandbytes for quantization
* MLflow for experiment tracking and model registry
* vLLM for optimized serving
* Docker and OpenShift/Kubernetes for deployment

#### Workshop Structure & Milestones (1-Day Format)

**Timing:** 9:00 AM - 5:00 PM with breaks
- **9:00-9:30**: Introduction & Environment Setup
- **9:30-10:30**: Exercise 1: Model Exploration & Data Preparation
- **10:30-10:45**: Break
- **10:45-12:00**: Exercise 2: Instruction Tuning with LoRA/QLoRA
- **12:00-1:00**: Lunch
- **1:00-2:15**: Exercise 3: Model Evaluation & Tracking
- **2:15-2:30**: Break
- **2:30-3:45**: Exercise 4: Model Versioning & Packaging
- **3:45-4:00**: Break
- **4:00-5:00**: Exercise 5: Deployment & Serving on OpenShift

#### Actionable Steps for Implementation

**Milestone 1: Repository Structure Setup**
- Create directory: `labs/02_intermediate/02_llm_instruction_tuning/`
- Create subdirectories: `notebooks/`, `scripts/`, `data/`, `models/`, `k8s/`
- Create base files: `README.md`, `requirements.txt`, `environment.yml`, `Dockerfile`
- Create documentation directory: `docs/labs-docs/02_intermediate/llm-instruction-tuning/`
- Create main overview: `docs/labs-docs/02_intermediate/llm-instruction-tuning.md`

**Milestone 2: Exercise 1 - Setup & Exploration**
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/01_setup_exploration.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/01_setup_exploration.md`
- Implement: Environment check, base model loading (TinyLlama/Phi-2), tokenization exploration
- Document: GPU memory constraints, model architecture basics

**Milestone 3: Exercise 2 - Data Preparation**
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/02_data_preparation.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/02_data_preparation.md`
- Implement: Dataset loading (dolly-15k subset), instruction formatting, train/validation split
- Document: Data preprocessing for LLMs, prompt engineering basics

**Milestone 4: Exercise 3 - LoRA Tuning**
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/03_lora_tuning.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/03_lora_tuning.md`
- Implement: LoRA/QLoRA configuration, training loop with MLflow tracking, memory optimization
- Document: Parameter-efficient fine-tuning concepts, quantization benefits

**Milestone 5: Exercise 4 - Evaluation**
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/04_evaluation.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/04_evaluation.md`
- Implement: Perplexity calculation, qualitative comparison, MLflow experiment comparison
- Document: LLM evaluation challenges, human-in-the-loop assessment

**Milestone 6: Exercise 5 - Versioning & Packaging**
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/05_versioning_packaging.ipynb`
- Create scripts: `build_and_push.sh`, `mlflow_register.py`
- Create Dockerfile: `labs/02_intermediate/02_llm_instruction_tuning/Dockerfile`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/05_versioning_packaging.md`
- Implement: Model registration in MLflow, LoRA weight merging, containerization
- Document: Model versioning best practices, container optimization for LLMs

**Milestone 7: Exercise 6 - Deployment & Serving**
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/06_deployment_serving.ipynb`
- Create k8s manifests: `deployment.yaml`, `service.yaml` in `k8s/` subdirectory
- Create test script: `test_client.py`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/06_deployment_serving.md`
- Implement: OpenShift deployment configuration, resource limits, service testing
- Document: Kubernetes-native LLM serving, lifecycle management concepts

**Milestone 8: Documentation Integration**
- Write main overview: `docs/labs-docs/02_intermediate/llm-instruction-tuning.md`
- Link to existing intermediate lab documentation
- Ensure consistent formatting with bike-demand-forecasting.md
- Add navigation references in workshop-overview.md

**Milestone 9: Validation & Testing**
- Test all exercises in OpenShift AI notebook environment
- Verify MLflow tracking works correctly
- Test container build and deployment to OpenShift
- Validate all documentation renders correctly in MkDocs
- Fix any issues discovered during testing

### Key Technologies

- **MkDocs Material Theme**: Documentation site with dark/light mode support
- **MLflow**: Experiment tracking and model registry
- **Kubeflow Pipelines**: Pipeline orchestration (Intermediate level)
- **Evidently**: Model monitoring and drift detection
- **FastAPI**: Model serving REST API
- **OpenShift/Kubernetes**: Container orchestration for deployment
- **scikit-learn**: ML framework (Random Forest Regressor)
- **Hugging Face Transformers & PEFT**: LLM fine-tuning libraries (LLMOps level)
- **bitsandbytes**: Quantization for efficient LLM training (LLMOps level)
- **vLLM**: Optimized LLM serving engine (LLMOps level)

### MLOps Pipeline Flow

The bike demand forecasting exercise follows this flow:

1. **Data Exploration** (`01_data_exploration.ipynb`): Load and explore the UCI bike sharing dataset
2. **Data Preparation** (`02_data_preparation.ipynb`): Clean, preprocess, and split data
3. **Model Training** (`03_model_training.ipynb`): Train Random Forest models with hyperparameter tuning
4. **Model Registration** (`04_model_registeration.ipynb`): Register best model in MLflow Model Registry
5. **Model Testing** (`05_model_testing_endpoint.ipynb`): Test the registered model
6. **Model Monitoring** (`06_model_monitoring.ipynb`): Set up Evidently for drift detection

### LLMOps Workshop Exercise Flow

The LLM instruction tuning exercise follows this flow:

1. **Setup & Exploration** (`01_setup_exploration.ipynb`): Launch OpenShift AI notebook, explore base model (TinyLlama/Phi-2), understand resource constraints
2. **Data Preparation** (`02_data_preparation.ipynb`): Load and format instruction dataset, tokenize, create train/validation splits
3. **LoRA Tuning** (`03_lora_tuning.ipynb`): Configure parameter-efficient fine-tuning with LoRA/QLoRA, train with MLflow tracking, save adapter to `./lora_adapter/`
4. **Evaluation** (`04_evaluation.ipynb`): Evaluate model performance with perplexity and qualitative assessment, compare experiments in MLflow via `MlflowClient().search_experiments()`
5. **Versioning & Packaging** (`05_versioning_packaging.ipynb`): Load adapter from `./lora_adapter/`, log model weights to MLflow via `mlflow.pytorch.log_model()`, register in Model Registry, merge weights and save to `../models/merged_model` (lab root), create Docker container with vLLM serving
6. **Deployment & Serving** (`06_deployment_serving.ipynb`): Deploy to OpenShift/Kubernetes, configure resource limits, test endpoint

**Model Persistence Chain (notebook-to-notebook handoff):**

```
03 (train)  ──save──>  ./lora_adapter/          (local disk, PEFT adapter)
                │
04 (eval)   ──load──>  ./lora_adapter/          ✓ loads from local disk
                │
05 (package) ─load──>  ./lora_adapter/          ✓ loads from local disk
                │──log──>  MLflow (pytorch.log_model)  ✓ weights logged to artifacts
                │──save──>  ../models/merged_model     ✓ aligned with Dockerfile
                │
Dockerfile   ──copy──>  models/merged_model     ✓ expects same path
                │
06 (deploy)  ──test──>  http://localhost:8000    ✓ tests deployed endpoint
```

### Deployment Architecture

The model deployment uses:
- **FastAPI** (`models/app.py`): REST API for model inference
- **Containerfile** (`models/Containerfile`): Container definition for OpenShift
- **Kubernetes manifests** (`models/k8s_deployment.yaml`): Deployment and service definitions

### LLMOps Deployment Architecture

The LLM deployment uses:
- **vLLM** (`models/vllm_server.py`): Optimized LLM serving engine
- **Containerfile** (`labs/02_intermediate/02_llm_instruction_tuning/Dockerfile`): Container definition for OpenShift
- **Kubernetes manifests** (`labs/02_intermediate/02_llm_instruction_tuning/k8s/`): Deployment and service definitions

### Pipeline Automation

The Kubeflow pipeline (`pipeline_bike_sharing.py`) automates:
1. `get_dataset`: Downloads and extracts the bike sharing dataset
2. `process_dataset`: Cleans and processes data, splits by month
3. `train_model`: Trains models with hyperparameter tuning, logs to MLflow
4. `register_model`: Registers the best model in MLflow Model Registry

Environment variables used:
- `DATASET_URL`: URL to download the dataset
- `MLFLOW_REMOTE_TRACKING_SERVER`: MLflow tracking server URL
- `PARTICIPANT_FIRSTNAME`: Used for experiment naming

## GitHub Actions

The repository uses GitHub Actions for CI/CD (`.github/workflows/ci.yml`). The workflow handles automated testing and deployment to GitHub Pages.

## Important Notes

- The workshop is designed for the Red Hat demo environment (OpenShift AI)
- MLflow tracking server URL is typically `http://mlflow-tracking.mlflow.svc.cluster.local:80` in the demo environment
- Participant names are used to namespace experiments and models to avoid conflicts
- The pipeline uses the `quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703` base image
- The repository is currently on the `facelift` branch with restructured documentation and lab organization

## LLMOps Model Persistence

The model handoff between notebooks follows this chain:

1. **Notebook 03** saves the LoRA adapter to **local disk** (`./lora_adapter/`) — NOT to MLflow (only metrics are logged during training)
2. **Notebook 04** loads from `./lora_adapter/` (local disk)
3. **Notebook 05** loads from `./lora_adapter/` (local disk), then logs weights to MLflow via `mlflow.pytorch.log_model()`, merges, and saves to `../models/merged_model`
4. **Dockerfile** uses `COPY models/ /app/models/` — expects `models/merged_model` relative to lab root

The merged model is saved to `../models/merged_model` (relative to `notebooks/`) = `models/merged_model` (relative to lab root). This path is consumed by the Dockerfile's `COPY models/ /app/models/` instruction.

## MLflow API Notes

- Use `MlflowClient().search_experiments()` instead of `mlflow.list_experiments()` (removed from top-level API in newer MLflow versions)
- `mlflow.pytorch.log_model()` is used to persist model weights to MLflow artifact store; Hugging Face's `report_to="mlflow"` only logs metrics, not weights