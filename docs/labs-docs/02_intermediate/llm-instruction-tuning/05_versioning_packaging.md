# Exercise 5: Versioning & Packaging

In this exercise, you will register your model in MLflow, merge LoRA weights, and create a Docker container for serving.

## Learning Objectives

By the end of this exercise, you will be able to:
- Register models in MLflow Model Registry
- Merge LoRA weights with base model
- Containerize LLM serving applications
- Understand model versioning best practices

## Prerequisites

Before starting this exercise, ensure you have:
1. Completed Exercise 4: Evaluation
2. A fine-tuned LoRA adapter
3. MLflow tracking server configured

## Step 1: Register Model in MLflow

```python
import mlflow
import mlflow.pytorch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

# Load base model and adapter
base_model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
base_model = AutoModelForCausalLM.from_pretrained(base_model_name)
model = PeftModel.from_pretrained(base_model, "./lora_adapter")
tokenizer = AutoTokenizer.from_pretrained(base_model_name)

# Merge LoRA weights with base model
merged_model = model.merge_and_unload()

# Start MLflow run
mlflow.set_experiment("llm-model-registry")
with mlflow.start_run(run_name="merged-model-v1"):
    # Log parameters
    mlflow.log_param("base_model", base_model_name)
    mlflow.log_param("adapter_path", "./lora_adapter")
    mlflow.log_param("merged_model", True)
    
    # Log model
    mlflow.pytorch.log_model(
        pytorch_model=merged_model,
        artifact_path="model",
        registered_model_name="llm-instruction-tuning-model"
    )
    
    # Log tokenizer
    tokenizer.save_pretrained("./tokenizer")
    mlflow.log_artifacts("./tokenizer", "tokenizer")
    
    print(f"Model registered with version: {mlflow.last_active_run().info.run_id}")
```

## Step 2: Create Build Script

Create `build_and_push.sh`:

```bash
#!/bin/bash
# Build and push Docker image

# Set variables
IMAGE_NAME="llm-instruction-tuning"
VERSION="v1.0.0"
REGISTRY="your-registry.example.com"  # Change to your registry

# Build image
docker build -t $IMAGE_NAME:$VERSION .

# Tag for registry
docker tag $IMAGE_NAME:$VERSION $REGISTRY/$IMAGE_NAME:$VERSION

# Push to registry
docker push $REGISTRY/$IMAGE_NAME:$VERSION

echo "Image built and pushed: $REGISTRY/$IMAGE_NAME:$VERSION"
```

## Step 3: Create MLflow Registration Script

Create `mlflow_register.py`:

```python
import mlflow
import mlflow.pytorch
from transformers import AutoModelForCausalLM
from peft import PeftModel
import argparse

def register_model(base_model_path, adapter_path, model_name):
    # Load models
    base_model = AutoModelForCausalLM.from_pretrained(base_model_path)
    model = PeftModel.from_pretrained(base_model, adapter_path)
    merged_model = model.merge_and_unload()
    
    # Register in MLflow
    with mlflow.start_run():
        mlflow.pytorch.log_model(
            pytorch_model=merged_model,
            artifact_path="model",
            registered_model_name=model_name
        )
    
    print(f"Model {model_name} registered successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", required=True, help="Base model path")
    parser.add_argument("--adapter", required=True, help="Adapter path")
    parser.add_argument("--name", required=True, help="Model name")
    args = parser.parse_args()
    
    register_model(args.base_model, args.adapter, args.name)
```

## Step 4: Update Dockerfile for Merged Model

Your Dockerfile should copy the merged model:

```dockerfile
# ... previous lines ...
COPY models/merged_model/ /app/models/merged_model/
# ... rest unchanged ...
```

## Summary

You learned how to:
- Register models in MLflow Model Registry
- Merge LoRA weights for serving
- Create build scripts for containerization
- Package models for deployment

---

<div style="display: flex; justify-content: space-between;">
    <a href="04_evaluation.md" class="md-button">← Previous</a>
    <a href="06_deployment_serving.md" class="md-button">Next →</a>
</div>