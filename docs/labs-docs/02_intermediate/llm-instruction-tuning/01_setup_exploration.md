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

## Environment Setup

Let's start by checking our environment and installing any necessary packages.

### Checking GPU Availability

First, let's verify that we have access to a GPU and check its specifications.