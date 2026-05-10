# Exercise 2: Data Preparation

In this exercise, you will prepare the dataset for instruction tuning your LLM. You'll load a dataset, format it for instruction tuning, tokenize it, and create train/validation splits.

## Learning Objectives

By the end of this exercise, you will be able to:
- Load and explore instruction tuning datasets
- Format data using instruction templates
- Tokenize data for LLM training
- Create train/validation splits
- Understand data preprocessing best practices for LLMs

## Prerequisites

Before starting this exercise, ensure you have:
1. Completed Exercise 1: Setup & Exploration
2. A working environment with transformers, datasets, and other required libraries installed

## Step 1: Import Required Libraries

Let's start by importing the necessary libraries:

```python
import os
import json
from datasets import load_dataset, DatasetDict
from transformers import AutoTokenizer
import numpy as np
```

## Step 2: Load the Dataset

For instruction tuning, we'll use a subset of the Dolly dataset, which contains instruction-response pairs:

```python
# Load Dolly dataset (or any instruction tuning dataset)
raw_datasets = load_dataset("databricks/databricks-dolly-15k", split="train")

# Explore the dataset
print(f"Dataset size: {len(raw_datasets)}")
print(f"Columns: {raw_datasets.column_names}")
print(f"\nExample:")
print(raw_datasets[0])
```

## Step 3: Explore the Data

Let's understand the structure of our dataset:

```python
# Check the different categories of instructions
categories = [example["category"] for example in raw_datasets]
unique_categories = set(categories)
print(f"Unique categories: {unique_categories}")

# Look at examples from different categories
for category in list(unique_categories)[:3]:
    print(f"\n--- {category} ---")
    example = next(e for e in raw_datasets if e["category"] == category)
    print(f"Instruction: {example['instruction'][:100]}...")
    print(f"Response: {example['response'][:100]}...")
```

## Step 4: Format Data for Instruction Tuning

Now we'll format the data using an instruction template:

```python
# Define instruction template
def format_instruction(example):
    """Format instruction and response for training."""
    return f"""### Instruction:
{example['instruction']}

### Input:
{example.get('input', '')}

### Response:
{example['response']}"""

# Apply formatting to create text field
formatted_dataset = raw_datasets.map(
    lambda example: {"text": format_instruction(example)},
    remove_columns=raw_datasets.column_names
)

print("Formatted example:")
print(formatted_dataset[0]["text"])
```

## Step 5: Load Tokenizer and Tokenize Data

Now let's tokenize our data:

```python
# Load tokenizer
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Set padding token
tokenizer.pad_token = tokenizer.eos_token

# Tokenize function
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=512,
        padding="max_length",
        return_tensors=None
    )

# Tokenize dataset
tokenized_dataset = formatted_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["text"]
)

# Check token lengths
token_lengths = [len(x) for x in tokenized_dataset["input_ids"]]
print(f"Average tokens: {np.mean(token_lengths):.1f}")
print(f"Max tokens: {max(token_lengths)}")
print(f"Min tokens: {min(token_lengths)}")
```

## Step 6: Create Train/Validation Split

Now let's split our data:

```python
# Split into train and validation
train_val_split = tokenized_dataset.train_test_split(test_size=0.1, seed=42)

# Create DatasetDict
dataset_dict = DatasetDict({
    "train": train_val_split["train"],
    "validation": train_val_split["test"]
})

print(f"Training samples: {len(dataset_dict['train'])}")
print(f"Validation samples: {len(dataset_dict['validation'])}")
```

## Step 7: Save the Processed Dataset

Finally, let's save our processed dataset:

```python
# Save to disk
output_dir = "./data/processed"
dataset_dict.save_to_disk(output_dir)

print(f"Dataset saved to {output_dir}")

# Verify by loading back
loaded_dataset = DatasetDict.load_from_disk(output_dir)
print(f"Loaded dataset: {loaded_dataset}")
```

## Summary

In this exercise, you learned how to:
1. Load instruction tuning datasets
2. Explore and understand data structure
3. Format data using instruction templates
4. Tokenize data for LLM training
5. Create train/validation splits
6. Save processed datasets

---

<div markdown="1" style="display: flex; justify-content: space-between;">
[← Previous](01_setup_exploration.md){ .md-button }
[Next →](03_lora_tuning.md){ .md-button }
</div>