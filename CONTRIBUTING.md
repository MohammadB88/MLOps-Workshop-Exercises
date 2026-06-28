# Contributing to MLOps Workshop Exercises

Thank you for your interest in contributing to this project! We welcome contributions from data scientists, ML engineers, and DevOps professionals.

## How to Contribute

### 1. Reporting Issues
If you find a bug or have a suggestion, please [open an issue](https://github.com/MohammadB88/MLOps-Workshop-Exercises/issues). Provide as much detail as possible, including:
- A clear description of the issue.
- Steps to reproduce the problem.
- Your environment details (OS, Python version, etc.).

### 2. Proposing Changes
Before starting a large feature or a major refactor, it is recommended to open an issue first to discuss the proposed changes with the maintainer.

### 3. Making a Contribution
1. **Fork** the repository.
2. **Create a new branch** for your feature or fix: `git checkout -b feature/your-feature-name`.
3. **Implement your changes**. 
   - Follow existing code conventions.
   - Ensure new components are documented.
   - If adding tests, follow the patterns in `labs/02_intermediate/bike_demand_forecasting_pipeline/test_process_dataset.py`.
4. **Commit your changes** with clear, descriptive commit messages.
5. **Push to your fork** and submit a **Pull Request** to the `main` branch.

## Contribution Areas

- **New Labs**: Adding new exercises for the `03_advanced` section or filling the `wine_quality_TODO` placeholder.
- **Documentation**: Improving guides in `docs/` or adding troubleshooting tips.
- **Bug Fixes**: Fixing issues in the ML pipelines, FastAPI serving code, or Kubernetes manifests.
- **Optimizations**: Improving the efficiency of KFP components or reducing Docker image sizes.

## Standards & Quality

- **Code Style**: Follow PEP 8 for Python code.
- **KFP v2**: Use `@dsl.component` and proper type annotations for Kubeflow components.
- **MLflow**: Maintain consistent experiment naming and tracking patterns.
- **Documentation**: Ensure any new labs have corresponding markdown files in `docs/labs-docs/`.

## License
By contributing to this project, you agree that your contributions will be licensed under the [MIT License](LICENSE).
