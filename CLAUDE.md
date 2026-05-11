# CLAUDE.md

MLOps Workshop repository with hands-on exercises. Built with MkDocs, published to GitHub Pages.

## Project Structure

```
MLOps-Workshop-Exercises/
├── docs/                              # MkDocs documentation
│   ├── labs-docs/                     # Lab guides
│   │   ├── bike-demand-forecasting.md
│   │   ├── bike-forecasting/          # Step-by-step guides
│   │   ├── llm-instruction-tuning.md
│   │   └── llm-instruction-tuning/    # LLMOps step-by-step guides
│   └── assets/                        # Images, CSS, JS
├── labs/
│   ├── 01_beginner/02_bike_demand_forecasting/  # 6 notebooks
│   └── 02_intermediate/
│       ├── bike_demand_forecasting_pipeline/  # Kubeflow pipeline
│       └── 02_llm_instruction_tuning/            # LLMOps exercise
│           ├── notebooks/              # 6 Jupyter notebooks
│           ├── scripts/                # Helper scripts
│           ├── k8s/                    # Kubernetes manifests
│           ├── data/                   # Gitignored
│           └── models/                 # Gitignored
├── mkdocs.yml
└── requirements.txt
```

## Common Commands

```bash
# Documentation
pip install -r requirements.txt
mkdocs serve              # Local dev
mkdocs build              # Build
mkdocs gh-deploy --force  # Deploy to GitHub Pages

# Labs
cd labs/01_beginner/02_bike_demand_forecasting
pip install -r requirements.txt
jupyter lab
```

## Key Technologies

- **MkDocs Material Theme**: Documentation
- **MLflow**: Experiment tracking and model registry
- **Kubeflow Pipelines**: Pipeline orchestration
- **Evidently**: Model monitoring and drift detection
- **FastAPI**: Model serving REST API
- **OpenShift/Kubernetes**: Container orchestration
- **scikit-learn**: ML framework (Random Forest)
- **Hugging Face Transformers & PEFT**: LLM fine-tuning
- **bitsandbytes**: Quantization for LLM training
- **vLLM**: Optimized LLM serving

## Exercise Flows

### Bike Demand Forecasting (Beginner)

1. Data Exploration → Load UCI bike sharing dataset
2. Data Preparation → Clean, preprocess, split
3. Model Training → Train Random Forest with hyperparameter tuning
4. Model Registration → Register best model in MLflow
5. Model Testing → Test registered model
6. Model Monitoring → Set up Evidently for drift detection

### LLMOps Instruction Tuning (Intermediate)

1. Setup & Exploration → Load base model (TinyLlama/Phi-2)
2. Data Preparation → Format instruction dataset, tokenize
3. LoRA Tuning → Train with LoRA/QLoRA, MLflow tracking
4. Evaluation → Perplexity, qualitative assessment
5. Versioning & Packaging → Register in MLflow, merge weights, containerize
6. Deployment & Serving → Deploy to OpenShift/Kubernetes

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

## Deployment Architecture

### Bike Forecasting
- **FastAPI** (`models/app.py`): REST API
- **Containerfile** (`models/Containerfile`): Container definition
- **Kubernetes** (`models/k8s_deployment.yaml`): Deployment and service

### LLMOps
- **vLLM** (`models/vllm_server.py`): Optimized LLM serving
- **Dockerfile** (`labs/02_intermediate/02_llm_instruction_tuning/Dockerfile`)
- **Kubernetes** (`labs/02_intermediate/02_llm_instruction_tuning/k8s/`)

## Pipeline Automation

Kubeflow pipeline (`pipeline_bike_sharing.py`):
1. `get_dataset`: Download and extract dataset
2. `process_dataset`: Clean, process, split by month
3. `train_model`: Train with hyperparameter tuning, log to MLflow
4. `register_model`: Register best model in MLflow

*Planned enhancements:*
5. `serve_model`: Download registered model and create FastAPI serving endpoint
6. `monitor_model`: Perform data drift and model monitoring with Evidently

Environment variables:
- `DATASET_URL`: Dataset download URL
- `MLFLOW_REMOTE_TRACKING_SERVER`: MLflow tracking server URL
- `PARTICIPANT_FIRSTNAME`: Experiment naming

## Important Notes

- Designed for Red Hat demo environment (OpenShift AI)
- MLflow tracking server: `http://mlflow-tracking.mlflow.svc.cluster.local:80`
- Participant names namespace experiments to avoid conflicts
- Pipeline base image: `quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703`

## MLflow API Notes

- Use `MlflowClient().search_experiments()` instead of `mlflow.list_experiments()` (removed in newer versions)
- `mlflow.pytorch.log_model()` persists model weights; Hugging Face's `report_to="mlflow"` only logs metrics

## Planned Refinements for Intermediate Bike Demand Forecasting Lab

The intermediate bike demand forecasting lab (`labs/02_intermediate/bike_demand_forecasting_pipeline/`) is planned to be enhanced with the following improvements to provide a more comprehensive MLOps experience:

### 1. Add Model Serving Component
- Create a new component that downloads the registered model from MLflow
- Implement a FastAPI application for serving predictions with input validation
- Add health check endpoints and proper error handling

### 2. Add Model Monitoring Component
- Integrate Evidently for model monitoring and drift detection
- Generate data drift, target drift, and data quality reports
- Save HTML reports and log monitoring metrics to MLflow

### 3. Add Containerization and Deployment Files
- Create Containerfile/Dockerfile for building the model serving image
- Add Kubernetes manifests for deployment (Deployment, Service, Route/Ingress)
- Include instructions for deploying to OpenShift/Kubernetes

### 4. Improve Pipeline Robustness
- Enhance existing components with better error handling and input validation
- Add comprehensive logging and data validation checks
- Implement configuration through environment variables or pipeline parameters
- Add model validation before registration (minimum performance thresholds)

### 5. Add Comprehensive Documentation
- Create detailed documentation explaining the pipeline architecture
- Provide guidance on running and customizing the pipeline
- Include expected outputs, artifacts, and troubleshooting tips
- Connect concepts to the beginner lab for progressive learning

### 6. Implement Proper Artifact Management
- Ensure components use KFP's artifact handling correctly
- Add metadata to artifacts where appropriate
- Implement proper cleanup of temporary files

### 7. Add Testing and Validation
- Include unit tests for individual components
- Add data validation checks at each pipeline stage
- Implement model validation before registration