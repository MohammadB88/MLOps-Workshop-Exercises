# Workshop Overview

In this page, we will go through implementing MLOps concepts to several use cases. 

The diagram below illustrates the stages of the MLOps lifecycle.

<figure markdown>
  ![MLOps Lifecycle Diagram](assets/images/mlops-lifecycle-diagram.png){ loading=lazy }
  <figcaption></figcaption>
</figure>

You will complete the following exercises, based on the difficulty of the workshop:

### Beginner Level

* [Wine Quality Classifier](labs-docs/01_beginner/wine-quality-classifier.md)
* [Bike Forecasting](labs-docs/01_beginner/bike-forecasting.md)

### Intermediate Level

* [LLM Instruction Tuning](labs-docs/02_intermediate/llm-instruction-tuning.md)
* [Bike Demand Forecasting Pipeline](labs-docs/02_intermediate/bike-demand-forecasting-pipeline.md)

### Advanced Level

* [ML Security & Compliance](labs-docs/03_advanced/ml-security-compliance.md)
* [Advanced Kubeflow Pipelines](labs-docs/03_advanced/kubeflow-advanced.md)

```mermaid
graph LR
    B(Step 1: Beginner Level)
    B --> B1[Wine Quality Classifier]
    B --> B2[Bike Demand Forecasting]
    B1 --> I(Step 2: Intermediate Level)
    B2 --> I
    I --> I1[LLM Instruction Tuning]
    I --> I2[Kubeflow Pipeline]
    I1 --> A(Step 3: Advanced Level)
    I2 --> A
    A --> A1[ML Security & Compliance]
    A --> A2[Advanced Kubeflow Pipelines]
```