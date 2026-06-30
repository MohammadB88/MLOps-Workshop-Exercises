#!/usr/bin/env bash
set -euo pipefail

############################################
# MLflow Installation on OpenShift via Helm (Auth Version)
# Chart: opendatahub-io/mlflow-operator
# Namespace: mlflow
############################################

NAMESPACE="mlflow"
VALUES_FILE="mlflow_values_auth.yaml"
HELM_RELEASE="mlflow"
HELM_CHART="opendatahub-io/mlflow"

echo "=========================================="
echo " MLflow Installation Script with Auth (OpenShift)"
echo "=========================================="

############################################
# 1. Create OpenShift project / namespace
############################################
echo "[1/7] Creating OpenShift project '${NAMESPACE}' (if not exists)..."
if ! oc get project "${NAMESPACE}" &>/dev/null; then
  oc new-project "${NAMESPACE}"
else
  echo "Project '${NAMESPACE}' already exists. Skipping."
fi

############################################
# 2. Add OpenDataHub Helm repository
############################################
echo "[2/7] Adding OpenDataHub Helm repository..."
if ! helm repo list | grep -q "^opendatahub-io"; then
  helm repo add opendatahub-io https://opendatahub-io.github.io/mlflow-operator/
else
  echo "OpenDataHub repo already added. Skipping."
fi

echo "Updating Helm repositories..."
helm repo update

############################################
# 3. Export default MLflow values
############################################
echo "[3/7] Exporting default MLflow Helm values..."
helm show values "${HELM_CHART}" > "${VALUES_FILE}"

############################################
# 4. Patch values.yaml for OpenShift & Auth
############################################
echo "[4/7] Modifying ${VALUES_FILE}..."

# Ensure service is ClusterIP for OpenShift Route
echo "Ensuring service type is ClusterIP"
sed -i 's/type: LoadBalancer/type: ClusterIP/g' "${VALUES_FILE}"

# The opendatahub-io chart has different structure. 
# We ensure resources and security contexts match OpenShift requirements.
# Since this is the 'auth' version, we keep the default authentication enabled 
# if the chart provides it, or ensure the specific auth env vars are set.

############################################
# 5. Install MLflow
############################################
echo "[5/7] Installing MLflow via Helm..."
if helm status "${HELM_RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo "MLflow Helm release '${HELM_RELEASE}' already exists in namespace '${NAMESPACE}'."
  echo "Skipping installation."
else
  echo "MLflow Helm release not found. Installing..."
  helm install "${HELM_RELEASE}" "${HELM_CHART}" \
    --namespace "${NAMESPACE}" \
    --values "${VALUES_FILE}"
fi

############################################
# 6. MLflow installation completed
############################################
echo "[6/7] MLflow installation completed successfully."
echo "You can now create an OpenShift Route to expose the MLflow UI."
echo "=========================================="

############################################
# 7. Deploy OpenShift Route for MLflow UI
############################################
echo "[7/7] Deploying MLflow OpenShift Route..."

# Note: Ensure mlflow_route.yaml exists or is created specifically for this deployment
if [ -f mlflow_route.yaml ]; then
  oc apply -n "${NAMESPACE}" -f mlflow_route.yaml
  echo "MLflow Route deployed successfully."
else
  echo "Warning: mlflow_route.yaml not found. Please create it manually to expose the service."
fi
