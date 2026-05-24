# Advanced Kubeflow Pipelines

Hands-on exercises exploring advanced Kubeflow Pipelines (KFP) concepts including pipeline triggers, advanced workflow patterns, scheduling automation, resource optimization, and monitoring/debugging.

## Learning Objectives

- Configure time-based and event-based pipeline triggers
- Implement conditional execution, parallel loops, and fan-out/fan-in patterns
- Automate pipeline scheduling with recurring runs and performance-based retraining
- Optimize resource allocation (CPU, memory, GPU) and manage caching
- Implement monitoring, logging, metrics collection, and error handling

## Prerequisites

- KFP SDK 2.0+
- Access to a Kubernetes cluster with Kubeflow deployed
- `kubectl` configured for your cluster
- Python 3.10+

## Directory Structure

```
labs/03_advanced/kubeflow_advanced/
├── notebooks/
│   ├── 01_basic_triggers.ipynb          # Time & event-based pipeline triggers
│   ├── 02_advanced_workflows.ipynb      # Conditional, loops, fan-out/fan-in
│   ├── 03_scheduling_automation.ipynb   # Scheduling & automated retraining
│   ├── 04_optimization_scaling.ipynb    # Resource optimization & caching
│   └── 05_monitoring_debugging.ipynb    # Monitoring, logging, error handling
├── scripts/
│   ├── __init__.py
│   └── pipeline_helpers.py              # Pipeline creation, compilation, scheduling
├── requirements.txt
└── README.md
```

## Exercise Descriptions

### 01 - Basic Triggers
Learn how to configure time-based triggers using cron schedules, event-based triggers for reactive pipelines, and integration with Kubernetes CronJobs.

### 02 - Advanced Workflows
Master conditional branching with `dsl.Condition()`, parallel execution with `dsl.ParallelFor`, and fan-out/fan-in patterns for distributed processing.

### 03 - Scheduling and Automation
Implement recurring pipeline schedules, performance-driven retraining triggers, and integration with external monitoring systems.

### 04 - Optimization and Scaling
Configure CPU, memory, and GPU resource requests/limits. Manage caching behavior and implement efficient parallel execution with resource constraints.

### 05 - Monitoring and Debugging
Add structured logging, collect custom metrics, implement retry logic and error handling, and generate monitoring dashboard configurations.

## Technologies

| Technology | Purpose |
|------------|---------|
| KFP SDK 2.0+ | Pipeline definition and orchestration |
| Kubernetes | Container orchestration and scheduling |
| Kubeflow | ML platform on Kubernetes |
| kfp-kubernetes | KFP-Kubernetes integration |
| Python 3.11 | Component implementation |
