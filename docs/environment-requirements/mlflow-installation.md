# MLflow Installation on OpenShift (OpenDataHub)

This guide describes how to install MLflow on OpenShift using the OpenDataHub MLflow Operator Helm chart.

## Prerequisites

Before running the installation script, ensure you have the following tools installed and configured:

   - **git**: For cloning the operator repository.

   - **helm**: For managing the MLflow installation.

   - **oc (OpenShift CLI)**: For interacting with the OpenShift cluster.

## Installation Steps

1. **Prepare the environment:**
   Log in to the jumphost, clone the repository, and navigate to the root directory:
   ```bash
   git clone <repository-url>
   cd MLOps-Workshop-Exercises
   ```

2. **Run the installation script:**
   ```bash
   chmod +x environment_preparations/mlflow_odh_installation.sh
   ./environment_preparations/mlflow_odh_installation.sh
   ```

3. **Configure the installation:**

The script will prompt you for the following configurations:

   - **OpenShift namespace**: The project where MLflow will be deployed (default: `mlflow`).

   - **Helm release name**: The name of the Helm release (default: `mlflow`).

   - **Backend store URI**: The database URI (default: `sqlite:////mlflow/mlflow.db`).

   - **Persistent storage**: Whether to enable persistent storage (default: `true`) and its size (default: `2Gi`).

   - **Resource Limits**: CPU and Memory requests/limits.

   - **Authentication Mode**: 
      - **Disable auth**: Direct browser access (recommended for labs).
      - **Keep auth**: Secure access via OpenShift OAuth proxy.


4. **Verify the installation:**
   The script will automatically create the project, patch the chart, install MLflow via Helm, set up the OpenShift Route, and provide the final access URL.

## Post-Installation

- **Access MLflow UI**: Use the URL provided by the script at the end of the execution.
- **Add Workspaces**: To allow other namespaces to use MLflow, label them:
  ```bash
  oc label namespace <target-namespace> mlflow-enabled=true
  ```
  
## Uninstall MLflow
To uninstall MLflow from your OpenShift cluster, run the following commands:

```bash
helm uninstall mlflow -n mlflow
oc delete route mlflow -n mlflow
```
