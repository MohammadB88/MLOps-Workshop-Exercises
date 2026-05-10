#!/usr/bin/env python3
"""
MLflow model registration script.

This script loads a base model with a LoRA adapter, merges the weights,
and registers the merged model in MLflow Model Registry.
"""

import os
import sys
import argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import mlflow
import mlflow.pytorch


def parse_args():
    parser = argparse.ArgumentParser(
        description="Register a LoRA-tuned model in MLflow Model Registry"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        help="Base model name or path"
    )
    parser.add_argument(
        "--adapter-path",
        type=str,
        required=True,
        help="Path to the LoRA adapter"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="llm-instruction-tuning-model",
        help="Name for the registered model"
    )
    parser.add_argument(
        "--tracking-uri",
        type=str,
        default="file://./mlruns",
        help="MLflow tracking URI"
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default="llm-model-registry",
        help="MLflow experiment name"
    )
    return parser.parse_args()


def register_model(base_model_name, adapter_path, model_name, tracking_uri, experiment_name):
    """Load adapter, merge, and register the model in MLflow."""
    print(f"Loading base model: {base_model_name}")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )

    print(f"Loading LoRA adapter from: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)

    print("Merging LoRA weights with base model...")
    merged_model = model.merge_and_unload()

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    print(f"Registering model: {model_name}")
    with mlflow.start_run(run_name=f"merged-{model_name}"):
        mlflow.log_param("base_model", base_model_name)
        mlflow.log_param("adapter_path", adapter_path)

        mlflow.pytorch.log_model(
            pytorch_model=merged_model,
            artifact_path="model",
            registered_model_name=model_name
        )

        tokenizer.save_pretrained("./tokenizer")
        mlflow.log_artifacts("./tokenizer", "tokenizer")

    print(f"Model '{model_name}' registered successfully!")
    return model_name


if __name__ == "__main__":
    args = parse_args()
    register_model(
        base_model_name=args.base_model,
        adapter_path=args.adapter_path,
        model_name=args.model_name,
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name
    )
