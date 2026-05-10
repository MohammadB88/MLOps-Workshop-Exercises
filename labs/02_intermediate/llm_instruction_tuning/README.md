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