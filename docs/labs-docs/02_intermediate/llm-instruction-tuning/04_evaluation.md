# Exercise 4: Evaluation

In this exercise, you will evaluate your fine-tuned LLM using perplexity and qualitative assessment. You'll compare experiments in MLflow.

## Learning Objectives

By the end of this exercise, you will be able to:
- Calculate perplexity for language models
- Perform qualitative evaluation of model outputs
- Compare experiments in MLflow
- Understand LLM evaluation challenges

## Prerequisites

Before starting this exercise, ensure you have:
1. Completed Exercise 3: LoRA Tuning
2. A fine-tuned LoRA adapter
3. MLflow tracking set up

## Step 1: Calculate Perplexity

Perplexity measures how well the model predicts a sequence:

```python
import math
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

# Load base model and adapter
base_model = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
model = PeftModel.from_pretrained(base_model, "./lora_adapter")
tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

def calculate_perplexity(text, model, tokenizer):
    """Calculate perplexity for a given text."""
    encodings = tokenizer(text, return_tensors="pt")
    input_ids = encodings.input_ids
    
    with torch.no_grad():
        outputs = model(input_ids, labels=input_ids)
        loss = outputs.loss
        perplexity = math.exp(loss)
    
    return perplexity

# Test on validation set
example_text = "MLOps is the practice of deploying and maintaining ML models in production."
ppl = calculate_perplexity(example_text, model, tokenizer)
print(f"Perplexity: {ppl:.2f}")
```

## Step 2: Qualitative Evaluation

Compare base model vs fine-tuned model outputs:

```python
def generate_response(prompt, model, tokenizer):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=100, temperature=0.7)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

test_prompt = "Explain what MLOps is in simple terms."

# Generate with base model
base_response = generate_response(test_prompt, base_model, tokenizer)
fine_tuned_response = generate_response(test_prompt, model, tokenizer)

print("Base model:")
print(base_response)
print("\nFine-tuned model:")
print(fine_tuned_response)
```

## Step 3: Compare in MLflow

```python
import mlflow

# List experiments
from mlflow.tracking import MlflowClient
client = MlflowClient()
experiments = client.search_experiments()
for exp in experiments:
    print(f"{exp.name}: {exp.experiment_id}")

# Compare runs
runs = client.search_runs(experiment_ids=["<experiment_id>"])
for run in runs:
    print(f"Run {run.info.run_id}: Loss = {run.data.metrics.get('train_loss')}")
```

## Summary

You learned how to:
- Calculate perplexity for evaluation
- Perform qualitative comparisons
- Use MLflow for experiment comparison

---

<div markdown="1" style="display: flex; justify-content: space-between;">
[← Previous](03_lora_tuning.md){ .md-button }
[Next →](05_versioning_packaging.md){ .md-button }
</div>