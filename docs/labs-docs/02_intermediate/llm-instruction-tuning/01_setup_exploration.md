# Exercise 1: Setup & Exploration

## Objective

In this exercise, you will:
1. Launch and verify your OpenShift AI notebook environment
2. Explore the base model architecture (TinyLlama or Phi-2)
3. Understand GPU memory constraints and resource limitations
4. Perform basic tokenization and text generation
5. Set up MLflow tracking for your experiments

## Prerequisites

- Access to an OpenShift AI notebook environment
- The repository cloned and the current working directory set to `labs/02_intermediate/02_llm_instruction_tuning`
- Dependencies installed (`pip install -r requirements.txt`)

!!! tip "MLOps Perspective"
    LLMOps extends MLOps principles to large language models, focusing on efficient fine-tuning, tracking, and deployment of LLM systems.

## Step 1: Environment Check

Let's start by checking our environment and verifying GPU availability.

```python
import torch
import transformers
import mlflow

# Check GPU
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA devices: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Check library versions
print(f"Transformers: {transformers.__version__}")
print(f"PyTorch: {torch.__version__}")
```

## Step 2: Load the Base Model

Load TinyLlama, a small but capable 1.1B parameter model:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
print(f"Model loaded: {model_name}")
print(f"Parameters: {model.num_parameters() / 1e6:.1f}M")
```

## Step 3: Explore Tokenization

Understand how the tokenizer converts text to tokens:

```python
text = "MLOps combines machine learning and operations."
tokens = tokenizer(text)
decoded = tokenizer.decode(tokens.input_ids[0])

print(f"Original: {text}")
print(f"Token IDs: {tokens.input_ids[0]}")
print(f"Decoded: {decoded}")
print(f"Vocab size: {tokenizer.vocab_size}")
```

## Step 4: Test Text Generation

Try generating text with the base model before fine-tuning:

```python
prompt = "What is machine learning?"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    temperature=0.7,
    do_sample=True,
)

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response)
```

## Step 5: Set Up MLflow Tracking

Configure MLflow to track experiments:

```python
mlflow.set_tracking_uri("file://./mlruns")
mlflow.set_experiment("llm-lora-tuning")

# Log a test run
with mlflow.start_run(run_name="setup-test"):
    mlflow.log_param("model_name", model_name)
    mlflow.log_param("num_parameters", model.num_parameters())
    mlflow.log_metric("vocab_size", tokenizer.vocab_size)
    print(f"MLflow run: {mlflow.active_run().info.run_id}")
```

## Summary

In this exercise, you:
1. Verified your GPU environment and installed dependencies
2. Loaded TinyLlama, a 1.1B parameter language model
3. Explored how the tokenizer converts text to tokens
4. Generated text with the base model
5. Configured MLflow for experiment tracking

---

<div style="display: flex; justify-content: space-between;">
<a href="../llm-instruction-tuning.md" class="md-button">← Previous</a>
<a href="../02_data_preparation/" class="md-button">Next →</a>
</div>