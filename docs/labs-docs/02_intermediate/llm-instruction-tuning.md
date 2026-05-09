# LLMOps Instruction Tuning Workshop

This intermediate-level workshop extends MLOps concepts to large language model systems, focusing on instruction tuning workflows.

## Overview

In this workshop, you'll learn how to apply MLOps principles to LLM systems:
- Parameter-efficient fine-tuning with LoRA/QLoRA
- Experiment tracking with MLflow
- Model evaluation and versioning
- Containerization and Kubernetes-native deployment
- LLM serving lifecycle management

## Exercises

1. **Setup & Exploration**: Environment check, base model loading, tokenization exploration
2. **Data Preparation**: Instruction dataset loading, formatting, train/validation split
3. **LoRA Tuning**: Parameter-efficient fine-tuning with LoRA/QLoRA, MLflow tracking
4. **Evaluation**: Perplexity calculation, qualitative assessment, experiment comparison
5. **Versioning & Packaging**: Model registration in MLflow, Docker packaging for vLLM serving
6. **Deployment & Serving**: OpenShift deployment, resource configuration, service testing

## Prerequisites

- OpenShift AI notebook environment
- Basic understanding of Python and machine learning
- Familiarity with MLOps concepts from the beginner workshop

## Technologies Used

- Hugging Face Transformers and PEFT for model tuning
- bitsandbytes for quantization
- MLflow for experiment tracking and model registry
- vLLM for optimized serving
- Docker and OpenShift/Kubernetes for deployment

## Getting Started

1. Navigate to this directory in your OpenShift AI notebook
2. Install dependencies: `pip install -r requirements.txt`
3. Begin with Exercise 1: `notebooks/01_setup_exploration.ipynb`

## Workshop Structure & Milestones (1-Day Format)

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

## Actionable Steps for Implementation

### Milestone 1: Repository Structure Setup ✓
- Created directory: `labs/02_intermediate/02_llm_instruction_tuning/`
- Created subdirectories: `notebooks/`, `scripts/`, `data/`, `models/`, `k8s/`
- Created base files: `README.md`, `requirements.txt`, `environment.yml`
- Created documentation directory: `docs/labs-docs/02_intermediate/llm-instruction-tuning/`
- Created main overview: `docs/labs-docs/02_intermediate/llm-instruction-tuning.md`

### Milestone 2: Exercise 1 - Setup & Exploration
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/01_setup_exploration.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/01_setup_exploration.md`
- Implement: Environment check, base model loading (TinyLlama/Phi-2), tokenization exploration
- Document: GPU memory constraints, model architecture basics

### Milestone 3: Exercise 2 - Data Preparation
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/02_data_preparation.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/02_data_preparation.md`
- Implement: Dataset loading (dolly-15k subset), instruction formatting, train/validation split
- Document: Data preprocessing for LLMs, prompt engineering basics

### Milestone 4: Exercise 3 - LoRA Tuning
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/03_lora_tuning.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/03_lora_tuning.md`
- Implement: LoRA/QLoRA configuration, training loop with MLflow tracking, memory optimization
- Document: Parameter-efficient fine-tuning concepts, quantization benefits

### Milestone 5: Exercise 4 - Evaluation
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/04_evaluation.ipynb`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/04_evaluation.md`
- Implement: Perplexity calculation, qualitative comparison, MLflow experiment comparison
- Document: LLM evaluation challenges, human-in-the-loop assessment

### Milestone 6: Exercise 5 - Versioning & Packaging
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/05_versioning_packaging.ipynb`
- Create scripts: `build_and_push.sh`, `mlflow_register.py`
- Create Dockerfile: `labs/02_intermediate/02_llm_instruction_tuning/Dockerfile`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/05_versioning_packaging.md`
- Implement: Model registration in MLflow, LoRA weight merging, containerization
- Document: Model versioning best practices, container optimization for LLMs

### Milestone 7: Exercise 6 - Deployment & Serving
- Create notebook: `labs/02_intermediate/02_llm_instruction_tuning/notebooks/06_deployment_serving.ipynb`
- Create k8s manifests: `deployment.yaml`, `service.yaml` in `k8s/` subdirectory
- Create test script: `test_client.py`
- Create instructions: `docs/labs-docs/02_intermediate/llm-instruction-tuning/06_deployment_serving.md`
- Implement: OpenShift deployment configuration, resource limits, service testing
- Document: Kubernetes-native LLM serving, lifecycle management concepts

### Milestone 8: Documentation Integration ✓
- Wrote main overview: `docs/labs-docs/02_intermediate/llm-instruction-tuning.md`
- Linked to existing intermediate lab documentation
- Ensured consistent formatting with bike-demand-forecasting.md
- Added navigation references in workshop-overview.md

### Milestone 9: Validation & Testing
- Test all exercises in OpenShift AI notebook environment
- Verify MLflow tracking works correctly
- Test container build and deployment to OpenShift
- Validate all documentation renders correctly in MkDocs
- Fix any issues discovered during testing