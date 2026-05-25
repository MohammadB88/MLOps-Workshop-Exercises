# Exercise 3: LoRA Tuning

In this exercise, you will perform parameter-efficient fine-tuning using LoRA (Low-Rank Adaptation) on your base model. You'll learn how to configure LoRA, train efficiently, and save adapters.

## Learning Objectives

By the end of this exercise, you will be able to:
- Understand parameter-efficient fine-tuning concepts
- Configure LoRA for efficient model adaptation
- Implement training with MLflow tracking
- Monitor GPU memory during training
- Save and load LoRA adapters

## Prerequisites

Before starting this exercise, ensure you have:
1. Completed Exercise 2: Data Preparation
2. Access to a GPU (recommended)
3. MLflow tracking server configured

## Step 1: Import Libraries and Setup

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_int8_training
import mlflow
```

## Step 2: Load Base Model with Quantization

```python
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Load model with 4-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_4bit=True,
    device_map="auto",
    torch_dtype=torch.float16,
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
```

## Step 3: Configure LoRA

```python
# Prepare model for int8 training
model = prepare_model_for_int8_training(model)

# LoRA configuration
lora_config = LoraConfig(
    r=16,  # Rank
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

## Step 4: Configure Training

```python
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=1,
    save_strategy="epoch",
    report_to="mlflow",
)
```

## Step 5: Train and Track with MLflow

```python
mlflow.set_experiment("llm-lora-tuning")

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

trainer.train()
model.save_pretrained("./lora_adapter")
```

## Summary

You learned how to:
- Apply LoRA for parameter-efficient fine-tuning
- Train with MLflow tracking
- Save LoRA adapters for deployment

---

