#!/usr/bin/env bash
set -euo pipefail

############################################
# MLflow Installation on OpenShift via Helm
# Using OpenDataHub MLflow Operator Chart
# Source: https://github.com/opendatahub-io/mlflow-operator
############################################

echo "=========================================="
echo " MLflow Installation Script (OpenShift)"
echo " OpenDataHub MLflow Operator Chart"
echo "=========================================="

############################################
# Check prerequisites
############################################
if ! command -v git &>/dev/null; then
  echo "ERROR: git is not installed. Please install git first."
  exit 1
fi

if ! command -v helm &>/dev/null; then
  echo "ERROR: helm is not installed. Please install helm first."
  exit 1
fi

if ! command -v oc &>/dev/null; then
  echo "ERROR: oc (OpenShift CLI) is not installed. Please install oc first."
  exit 1
fi

############################################
# Collect user input
############################################
echo ""
echo "Please provide the following information:"

# Default namespace
NAMESPACE_DEFAULT="mlflow"
read -p "OpenShift namespace (default: ${NAMESPACE_DEFAULT}): " NAMESPACE_INPUT
NAMESPACE="${NAMESPACE_INPUT:-$NAMESPACE_DEFAULT}"

# Helm release name
RELEASE_DEFAULT="mlflow"
read -p "Helm release name (default: ${RELEASE_DEFAULT}): " RELEASE_INPUT
RELEASE="${RELEASE_INPUT:-$RELEASE_DEFAULT}"

# Backend store URI
echo ""
echo "Backend store URI configuration:"
echo "  - For local file storage (requires storage.enabled: true): sqlite:////mlflow/mlflow.db"
echo "  - For PostgreSQL: postgresql://user:password@host:5432/mlflow"
echo "  - Leave empty to configure via secret later"
read -p "Backend store URI (default: sqlite:////mlflow/mlflow.db): " BACKEND_URI
BACKEND_URI="${BACKEND_URI:-sqlite:////mlflow/mlflow.db}"

# Storage configuration
STORAGE_DEFAULT="true"
read -p "Enable persistent storage (default: ${STORAGE_DEFAULT}): " STORAGE_INPUT
STORAGE_ENABLED="${STORAGE_INPUT:-$STORAGE_DEFAULT}"

# Storage size
STORAGE_SIZE_DEFAULT="2Gi"
read -p "Storage size (default: ${STORAGE_SIZE_DEFAULT}): " STORAGE_SIZE_INPUT
STORAGE_SIZE="${STORAGE_SIZE_INPUT:-$STORAGE_SIZE_DEFAULT}"

# Resource configuration
CPU_REQUEST_DEFAULT="1"
MEMORY_REQUEST_DEFAULT="2Gi"
CPU_LIMIT_DEFAULT="4"
MEMORY_LIMIT_DEFAULT="3Gi"

read -p "CPU request (default: ${CPU_REQUEST_DEFAULT}): " CPU_REQUEST_INPUT
CPU_REQUEST="${CPU_REQUEST_INPUT:-$CPU_REQUEST_DEFAULT}"

read -p "Memory request (default: ${MEMORY_REQUEST_DEFAULT}): " MEMORY_REQUEST_INPUT
MEMORY_REQUEST="${MEMORY_REQUEST_INPUT:-$MEMORY_REQUEST_DEFAULT}"

read -p "CPU limit (default: ${CPU_LIMIT_DEFAULT}): " CPU_LIMIT_INPUT
CPU_LIMIT="${CPU_LIMIT_INPUT:-$CPU_LIMIT_DEFAULT}"

read -p "Memory limit (default: ${MEMORY_LIMIT_DEFAULT}): " MEMORY_LIMIT_INPUT
MEMORY_LIMIT="${MEMORY_LIMIT_INPUT:-$MEMORY_LIMIT_DEFAULT}"

# Replica count
REPLICAS_DEFAULT="1"
read -p "Number of replicas (default: ${REPLICAS_DEFAULT}): " REPLICAS_INPUT
REPLICAS="${REPLICAS_INPUT:-$REPLICAS_DEFAULT}"

VALUES_FILE="mlflow_odh_values.yaml"
MLFLOW_OPERATOR_REPO="https://github.com/opendatahub-io/mlflow-operator.git"
MLFLOW_CHART_DIR="mlflow-operator-charts"

echo ""
echo "=========================================="
echo " Configuration Summary"
echo "=========================================="
echo "Namespace: ${NAMESPACE}"
echo "Helm Release: ${RELEASE}"
echo "Backend Store URI: ${BACKEND_URI}"
echo "Storage Enabled: ${STORAGE_ENABLED}"
echo "Storage Size: ${STORAGE_SIZE}"
echo "CPU Request: ${CPU_REQUEST}"
echo "Memory Request: ${MEMORY_REQUEST}"
echo "CPU Limit: ${CPU_LIMIT}"
echo "Memory Limit: ${MEMORY_LIMIT}"
echo "Replicas: ${REPLICAS}"
echo "=========================================="
echo ""
read -p "Continue with these settings? (y/n): " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
  echo "Installation cancelled."
  exit 0
fi

############################################
# 1. Create OpenShift project / namespace
############################################
echo "[1/9] Creating OpenShift project '${NAMESPACE}' (if not exists)..."
if ! oc get project "${NAMESPACE}" &>/dev/null; then
  oc new-project "${NAMESPACE}"
else
  echo "Project '${NAMESPACE}' already exists. Skipping."
fi

############################################
# 2. Detect OpenShift cluster URL
############################################
echo "[2/9] Detecting OpenShift cluster URL..."
API_URL=$(oc whoami --show-server)
echo "OpenShift API server: ${API_URL}"

CLUSTER_DOMAIN=$(echo "${API_URL}" | sed -E 's|^https://api\.||; s|:6443$||')
ALLOWED_HOSTS="*.apps.${CLUSTER_DOMAIN}"

echo "Detected apps domain: *.apps.${CLUSTER_DOMAIN}"
read -p "Is this correct for the OpenShift apps domain? (y/n): " DOMAIN_CONFIRM
if [[ "${DOMAIN_CONFIRM}" != "y" && "${DOMAIN_CONFIRM}" != "Y" ]]; then
  read -p "Enter the correct apps domain (e.g. apps.ocp.example.com): " CUSTOM_DOMAIN
  ALLOWED_HOSTS="*.${CUSTOM_DOMAIN}"
fi
echo "MLflow allowedHosts will be set to: ${ALLOWED_HOSTS}"

############################################
# 3. Clone MLflow Operator repository
############################################
echo "[3/9] Cloning MLflow Operator repository..."
if [[ -d "${MLFLOW_CHART_DIR}" ]]; then
  echo "Chart directory already exists. Updating..."
  git -C "${MLFLOW_CHART_DIR}" pull
else
  git clone --depth 1 "${MLFLOW_OPERATOR_REPO}" "${MLFLOW_CHART_DIR}"
fi

############################################
# 4. Create custom values.yaml
############################################
echo "[4/9] Creating custom MLflow values file..."

cat > "${VALUES_FILE}" <<EOF
# MLflow OpenDataHub Installation Values
# Generated by automated installation script

namespace: ${NAMESPACE}

resourceSuffix: ""

commonLabels:
  component: mlflow
  app: mlflow

podLabels:
  app: mlflow

podAnnotations: {}

tls:
  secretName: mlflow-tls
  defaultMode: 416

replicaCount: ${REPLICAS}

image:
  name: quay.io/opendatahub/mlflow:latest

serviceAccount:
  name: mlflow-sa

resources:
  requests:
    cpu: "${CPU_REQUEST}"
    memory: ${MEMORY_REQUEST}
  limits:
    cpu: "${CPU_LIMIT}"
    memory: ${MEMORY_LIMIT}

storage:
  enabled: ${STORAGE_ENABLED}
  size: ${STORAGE_SIZE}
  storageClassName: ""
  accessMode: ReadWriteOnce

mlflow:
  backendStoreUri: "${BACKEND_URI}"
  artifactsDestination: "file:///mlflow/artifacts"
  enableWorkspaces: true
  workspaceStoreUri: "kubernetes://"
  serveArtifacts: true
  workers: 1
  port: 8443
  allowedHosts:
    - "${ALLOWED_HOSTS}"
  corsAllowedOrigins: ""
  staticPrefix: ""

env:
  - name: MLFLOW_LOGGING_LEVEL
    value: INFO

podSecurityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL

service:
  type: ClusterIP
  port: 8443
  annotations:
    service.beta.openshift.io/serving-cert-secret-name: mlflow-tls

metrics:
  enabled: true

networkPolicy:
  egressRules: []
  additionalEgressRules: []

nodeSelector: {}
tolerations: []
affinity: {}

garbageCollection:
  enabled: false
  schedule: "0 2 * * 0"
  serviceAccount:
    name: mlflow-gc-sa
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

caBundle:
  filePaths: []
  configMaps: []
  outputPath: /etc/pki/tls/certs/combined/ca-bundle.crt
  watchInterval: 30
EOF

echo "Values file created: ${VALUES_FILE}"

############################################
# 5. Install MLflow
############################################
echo "[5/9] Installing MLflow via Helm..."
HELM_CHART_PATH="${MLFLOW_CHART_DIR}/charts/mlflow"
if helm status "${RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo "MLflow Helm release '${RELEASE}' already exists in namespace '${NAMESPACE}'."
  read -p "Upgrade existing release? (y/n): " UPGRADE
  if [[ "${UPGRADE}" == "y" || "${UPGRADE}" == "Y" ]]; then
    echo "Upgrading existing release..."
    helm upgrade "${RELEASE}" "${HELM_CHART_PATH}" \
      --namespace "${NAMESPACE}" \
      --values "${VALUES_FILE}"
  else
    echo "Skipping installation."
  fi
else
  echo "MLflow Helm release not found. Installing..."
  helm install "${RELEASE}" "${HELM_CHART_PATH}" \
    --namespace "${NAMESPACE}" \
    --values "${VALUES_FILE}"
fi

############################################
# 6. Verify installation
############################################
echo "[6/9] Verifying MLflow installation..."
sleep 5

if oc get deployment "${RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo "MLflow deployment found."
  oc get deployment "${RELEASE}" -n "${NAMESPACE}"
else
  echo "WARNING: MLflow deployment not found."
fi

if oc get pods -n "${NAMESPACE}" -l component=mlflow &>/dev/null; then
  echo ""
  echo "MLflow pods:"
  oc get pods -n "${NAMESPACE}" -l component=mlflow
fi

if helm status "${RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo ""
  echo "Helm release status:"
  helm status "${RELEASE}" -n "${NAMESPACE}"
fi

############################################
# 7. MLflow installation completed
############################################
echo ""
echo "[7/9] MLflow installation completed successfully."
echo ""

############################################
# 8. Deploy OpenShift Route for MLflow UI
############################################
echo "[8/9] Creating OpenShift Route for MLflow UI..."

cat > mlflow_route.yaml <<EOF
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${RELEASE}
  namespace: ${NAMESPACE}
  labels:
    component: mlflow
spec:
  to:
    kind: Service
    name: ${RELEASE}
  port:
    targetPort: https
  tls:
    termination: passthrough
EOF

if oc get route "${RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo "Route '${RELEASE}' already exists. Skipping."
else
  oc apply -n "${NAMESPACE}" -f mlflow_route.yaml
  echo "Route created successfully."
fi

############################################
# 9. Display access information
############################################
echo "[9/9] Access information"
echo "=========================================="
echo ""
echo "MLflow UI will be available at:"
HOSTNAME=$(oc get route "${RELEASE}" -n "${NAMESPACE}" -o jsonpath='{.spec.host}' 2>/dev/null || echo "pending")
if [[ "${HOSTNAME}" != "pending" ]]; then
  echo "  https://${HOSTNAME}"
else
  echo "  (Route hostname pending. Wait a few moments and check with:)"
  echo "  oc get route ${RELEASE} -n ${NAMESPACE}"
fi
echo ""
echo "Check pod status:"
echo "  oc get pods -n ${NAMESPACE} -l component=mlflow"
echo ""
echo "View logs:"
echo "  oc logs -n ${NAMESPACE} -l component=mlflow"
echo ""
echo "Uninstall MLflow:"
echo "  helm uninstall ${RELEASE} -n ${NAMESPACE}"
echo "  oc delete route ${RELEASE} -n ${NAMESPACE}"
echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="