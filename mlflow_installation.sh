#!/usr/bin/env bash
set -euo pipefail

############################################
# MLflow Installation on OpenShift via Helm
# Namespace: mlflow
############################################

NAMESPACE="mlflow"
VALUES_FILE="mlflow_values.yaml"
HELM_RELEASE="mlflow"
HELM_CHART="bitnami/mlflow"

echo "=========================================="
echo " MLflow Installation Script (OpenShift)"
echo "=========================================="

############################################
# 1. Create OpenShift project / namespace
############################################
echo "[1/6] Creating OpenShift project '${NAMESPACE}' (if not exists)..."
if ! oc get project "${NAMESPACE}" &>/dev/null; then
  oc new-project "${NAMESPACE}"
else
  echo "Project '${NAMESPACE}' already exists. Skipping."
fi

############################################
# 2. Add Bitnami Helm repository
############################################
echo "[2/6] Adding Bitnami Helm repository..."
if ! helm repo list | grep -q "^bitnami"; then
  helm repo add bitnami https://charts.bitnami.com/bitnami
else
  echo "Bitnami repo already added. Skipping."
fi

echo "Updating Helm repositories..."
helm repo update

############################################
# 3. Export default MLflow values
############################################
echo "[3/6] Exporting default MLflow Helm values..."
helm show values "${HELM_CHART}" > "${VALUES_FILE}"

############################################
# 4. Patch values.yaml
############################################
echo "[4/6] Modifying ${VALUES_FILE}..."

# Change service type from LoadBalancer to ClusterIP
echo "hange service type from LoadBalancer to ClusterIP"
sed -i 's/type: LoadBalancer/type: ClusterIP/g' "${VALUES_FILE}"


# Disable authentication for MLflow tracking server only
echo "Disable authentication for MLflow tracking server only"
sed -i '/tracking:/,/auth:/,/enabled:/ s/enabled: true/enabled: false/' "${VALUES_FILE}"

# # Disable authentication
# sed -i 's/enabled: true/enabled: false/g' "${VALUES_FILE}"

# Replace image repositories with bitnamilegacy
echo "Replace image repositories with bitnamilegacy"
sed -i 's|bitnami/mlflow|bitnamilegacy/mlflow|g' "${VALUES_FILE}"
sed -i 's|bitnami/os-shell|bitnamilegacy/os-shell|g' "${VALUES_FILE}"
sed -i 's|bitnami/git|bitnamilegacy/git|g' "${VALUES_FILE}"

# Disable PostgreSQL
echo "Disable PostgreSQL"
sed -i '/^postgresql:/,/^[^ ]/ s/enabled: true/enabled: false/' "${VALUES_FILE}"

# Disable MinIO
echo "Disable MinIO"
sed -i '/^minio:/,/^[^ ]/ s/enabled: true/enabled: false/' "${VALUES_FILE}"


# # Disable PostgreSQL
# cat <<EOF >> "${VALUES_FILE}"

# # Workaround: Disable PostgreSQL
# postgresql:
#   enabled: false

# # Workaround: Disable MinIO
# minio:
#   enabled: false
# EOF

############################################
# 5. Install MLflow
############################################
echo "[5/6] Installing MLflow via Helm..."
helm install "${HELM_RELEASE}" "${HELM_CHART}" \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_FILE}"

############################################
# 6. Done
############################################
echo "[6/6] MLflow installation completed successfully."
echo "You can now create an OpenShift Route to expose the MLflow UI."
echo "=========================================="
