# LLM Instruction Tuning Workshop

<!-- ![LLM logo](../assets/images/llm_logo.png) -->

This intermediate-level workshop extends MLOps concepts to large language model systems, focusing on instruction tuning workflows with LoRA/QLoRA.

## Introduction

Large Language Models (LLMs) have revolutionized natural language processing, but fine-tuning them for specific tasks traditionally requires substantial computational resources. **Parameter-Efficient Fine-Tuning (PEFT)** techniques like LoRA (Low-Rank Adaptation) make it practical to adapt LLMs on consumer-grade hardware by training only a small fraction of the parameters.

In this workshop, you'll learn how to apply MLOps principles to LLM systems:

- Parameter-efficient fine-tuning with LoRA/QLoRA
- Experiment tracking with MLflow
- Model evaluation and versioning in MLflow Model Registry
- Containerization and Kubernetes-native deployment
- LLM serving lifecycle management with vLLM

## Overview of the Exercises

The workshop follows the lifecycle of an LLM serving application:

1. **Setup & Exploration** — Verify your environment, load base models (TinyLlama/Phi-2), and explore tokenization
2. **Data Preparation** — Load and format the Dolly 15K instruction dataset, create train/validation splits
3. **LoRA Tuning** — Configure and run parameter-efficient fine-tuning with MLflow experiment tracking
4. **Evaluation** — Calculate perplexity, compare base vs. fine-tuned model outputs, navigate MLflow experiments
5. **Versioning & Packaging** — Register models in MLflow Model Registry, merge LoRA weights, create Docker images
6. **Deployment & Serving** — Deploy to OpenShift/Kubernetes, configure resource limits, test the endpoint

### Model: TinyLlama-1.1B

We use **[TinyLlama-1.1B](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0)** as our base model — a compact 1.1 billion parameter LLM that fits on consumer GPUs with 4-bit quantization. With LoRA, we can fine-tune it using only ~2-4 GB of GPU memory.

| Model | Parameters | FP16 Memory | 4-bit Quantized Memory |
|-------|-----------|-------------|----------------------|
| TinyLlama-1.1B | 1.1B | ~2.2 GB | ~0.6 GB |
| Phi-2 | 2.7B | ~5.4 GB | ~1.5 GB |

## Directory Structure

The workshop materials are organized for a complete MLOps workflow:

```
02_llm_instruction_tuning/
├── notebooks/
│   ├── 01_setup_exploration.ipynb
│   ├── 02_data_preparation.ipynb
│   ├── 03_lora_tuning.ipynb
│   ├── 04_evaluation.ipynb
│   ├── 05_versioning_packaging.ipynb
│   └── 06_deployment_serving.ipynb
├── scripts/
│   ├── build_and_push.sh
│   ├── mlflow_register.py
│   └── test_client.py
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── data/              # Datasets (gitignored)
├── models/            # Model outputs (gitignored)
├── Dockerfile
├── requirements.txt
├── environment.yml
└── README.md
```

## Prerequisites

- **OpenShift AI notebook environment** (or local GPU with 8GB+ VRAM)
- Basic understanding of Python and machine learning
- Familiarity with MLOps concepts from the beginner workshop
- Access to an OpenShift/Kubernetes cluster (for Exercise 6)

## Technologies Used

| Technology | Purpose |
|-----------|---------|
| [Hugging Face Transformers](https://huggingface.co/docs/transformers) | Model loading and inference |
| [PEFT](https://huggingface.co/docs/peft) | LoRA/QLoRA parameter-efficient fine-tuning |
| [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) | 4-bit quantization for memory efficiency |
| [MLflow](https://mlflow.org/) | Experiment tracking and model registry |
| [vLLM](https://github.com/vllm-project/vllm) | Optimized LLM serving engine |
| [FastAPI](https://fastapi.tiangolo.com/) | REST API serving framework |
| Docker / OpenShift | Containerization and orchestration |

## Getting Started

1. Launch an OpenShift AI notebook environment
2. Navigate to `labs/02_intermediate/02_llm_instruction_tuning/`
3. Install dependencies: `pip install -r requirements.txt`
4. Begin with Exercise 1 below

## Hands-On Sessions

Start with the setup exploration, then proceed through the exercises in order:

- [Exercise 1 - Setup & Exploration](llm-instruction-tuning/01_setup_exploration.md)
- [Exercise 2 - Data Preparation](llm-instruction-tuning/02_data_preparation.md)
- [Exercise 3 - LoRA Tuning](llm-instruction-tuning/03_lora_tuning.md)
- [Exercise 4 - Evaluation](llm-instruction-tuning/04_evaluation.md)
- [Exercise 5 - Versioning & Packaging](llm-instruction-tuning/05_versioning_packaging.md)
- [Exercise 6 - Deployment & Serving](llm-instruction-tuning/06_deployment_serving.md)

## Workshop Timing (1-Day Format)

| Time | Activity |
|------|----------|
| 9:00–9:30 | Introduction & Environment Setup |
| 9:30–10:30 | Exercise 1: Setup & Exploration |
| 10:30–10:45 | Break |
| 10:45–12:00 | Exercise 2: Data Preparation |
| 12:00–1:00 | Lunch |
| 1:00–2:15 | Exercise 3: LoRA Tuning |
| 2:15–2:30 | Break |
| 2:30–3:45 | Exercise 4: Evaluation |
| 3:45–4:00 | Break |
| 4:00–5:00 | Exercises 5 & 6: Packaging & Deployment |
