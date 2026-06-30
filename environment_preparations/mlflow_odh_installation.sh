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

if ! command -v openssl &>/dev/null; then
  echo "ERROR: openssl is not installed. Please install openssl first."
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

# Storage class selection
STORAGE_CLASS=""
if [[ "${STORAGE_ENABLED}" == "true" ]]; then
  echo ""
  echo "Available storage classes:"
  if ! SC_OUTPUT=$(oc get storageclass -o name 2>/dev/null) || [[ -z "${SC_OUTPUT}" ]]; then
    echo "  (No storage classes found or unable to query. Using cluster default.)"
  else
    echo ""
    mapfile -t SC_LIST < <(echo "${SC_OUTPUT}" | sed 's|storageclass.storage.k8s.io/||')
    for i in "${!SC_LIST[@]}"; do
      DEFAULT=$(oc get storageclass "${SC_LIST[$i]}" -o jsonpath='{.metadata.annotations.storageclass\.kubernetes\.io/is-default-class}' 2>/dev/null)
      DEFAULT_LABEL=""
      [[ "${DEFAULT}" == "true" ]] && DEFAULT_LABEL=" (default)"
      echo "  $((i+1))) ${SC_LIST[$i]}${DEFAULT_LABEL}"
    done
    echo ""
    read -p "Select storage class by number, or press Enter for cluster default: " SC_CHOICE
    if [[ -n "${SC_CHOICE}" && "${SC_CHOICE}" =~ ^[0-9]+$ && "${SC_CHOICE}" -le "${#SC_LIST[@]}" ]]; then
      STORAGE_CLASS="${SC_LIST[$((SC_CHOICE-1))]}"
      echo "Using storage class: ${STORAGE_CLASS}"
    else
      echo "Using cluster default storage class."
    fi
  fi
fi

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

# Authentication mode
echo ""
echo "MLflow authentication mode:"
echo "  1) Disable auth - Browser access works directly (recommended for labs/workshops)"
echo "  2) Keep auth + OAuth proxy - Secure browser access via OpenShift OAuth"
AUTH_DEFAULT="1"
read -p "Choose option (1 or 2, default: ${AUTH_DEFAULT}): " AUTH_CHOICE
AUTH_CHOICE="${AUTH_CHOICE:-$AUTH_DEFAULT}"
if [[ "${AUTH_CHOICE}" == "1" ]]; then
  MLFLOW_APP_NAME=""
  ENABLE_OAUTH_PROXY="false"
  echo "MLflow auth will be disabled. Browser access works directly."
else
  MLFLOW_APP_NAME="kubernetes-auth"
  ENABLE_OAUTH_PROXY="true"
  echo "MLflow auth will be kept. OpenShift OAuth proxy will be set up."
fi

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
echo "Storage Class: ${STORAGE_CLASS:-"(cluster default)"}"
echo "CPU Request: ${CPU_REQUEST}"
echo "Memory Request: ${MEMORY_REQUEST}"
echo "CPU Limit: ${CPU_LIMIT}"
echo "Memory Limit: ${MEMORY_LIMIT}"
echo "Replicas: ${REPLICAS}"
echo "Auth Mode: $([ -z "${MLFLOW_APP_NAME}" ] && echo 'Disabled (browser access)' || echo 'Enabled (kubernetes-auth)')"
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

echo "Labeling namespace '${NAMESPACE}' with mlflow-enabled=true for MLflow workspaces..."
oc label namespace "${NAMESPACE}" mlflow-enabled=true --overwrite

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
  APPS_DOMAIN="${CUSTOM_DOMAIN}"
else
  APPS_DOMAIN="apps.${CLUSTER_DOMAIN}"
fi
echo "MLflow allowedHosts will be set to: ${ALLOWED_HOSTS}"

############################################
# Pre-create OAuthClient and secrets for OAuth proxy
############################################
if [[ "${ENABLE_OAUTH_PROXY}" == "true" ]]; then
  ROUTE_HOSTNAME="${RELEASE}-${NAMESPACE}.${APPS_DOMAIN}"
  OAUTH_REDIRECT_URL="https://${ROUTE_HOSTNAME}/oauth/callback"

  echo ""
  echo "[*] Pre-creating OAuth resources for MLflow UI authentication..."
  echo "    Predicted Route hostname: ${ROUTE_HOSTNAME}"

  COOKIE_SECRET=$(openssl rand -base64 24)
  OAUTH_CLIENT_SECRET=$(openssl rand -base64 32)

  echo "    Creating OAuthClient 'mlflow-oauth-${RELEASE}'..."
  cat <<EOF | oc apply -f -
apiVersion: oauth.openshift.io/v1
kind: OAuthClient
metadata:
  name: mlflow-oauth-${RELEASE}
secret: ${OAUTH_CLIENT_SECRET}
redirectURIs:
  - "${OAUTH_REDIRECT_URL}"
grantMethod: auto
accessTokenMaxAgeSeconds: 28800
EOF

  echo "    Creating secret 'mlflow-oauth-${RELEASE}' in namespace '${NAMESPACE}'..."
  oc create secret generic "mlflow-oauth-${RELEASE}" \
    --from-literal=cookie-secret="${COOKIE_SECRET}" \
    --from-literal=client-secret="${OAUTH_CLIENT_SECRET}" \
    -n "${NAMESPACE}" --dry-run=client -o yaml | oc apply -f -

  echo "    OAuth resources created."
  echo ""
fi

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

echo "Patching chart deployment template to make auth configurable..."
export MLFLOW_CHART_DIR
python << 'PYEOF'
import os
import re
chart_dir = os.environ['MLFLOW_CHART_DIR']
path = f'{chart_dir}/charts/mlflow/templates/deployment.yaml'
with open(path, 'r') as f:
    content = f.read()
content = content.replace(
    '            - --app-name=kubernetes-auth',
    '{{- if .Values.mlflow.appName }}\n            - --app-name={{ .Values.mlflow.appName }}\n{{- end }}'
)
content = content.replace(
    '            - --enable-workspaces\n            - --workspace-store-uri={{ .Values.mlflow.workspaceStoreUri }}',
    '{{- if .Values.mlflow.enableWorkspaces }}\n            - --enable-workspaces\n            - --workspace-store-uri={{ .Values.mlflow.workspaceStoreUri }}\n{{- end }}'
)
with open(path, 'w') as f:
    f.write(content)
PYEOF
echo "Deployment template patched."

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
  storageClassName: "${STORAGE_CLASS}"
  accessMode: ReadWriteOnce

mlflow:
  appName: "${MLFLOW_APP_NAME}"
  backendStoreUri: "${BACKEND_URI}"
  artifactsDestination: "file:///mlflow/artifacts"
  enableWorkspaces: false
  workspaceStoreUri: ""
  workspaceLabelSelector: ""
  serveArtifacts: true
  workers: 1
  port: 8443
  allowedHosts:
    - "${ALLOWED_HOSTS}"
  corsAllowedOrigins: "*"
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
INSTALL_OCCURRED=false
if helm status "${RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo "MLflow Helm release '${RELEASE}' already exists in namespace '${NAMESPACE}'."
  read -p "Upgrade existing release? (y/n): " UPGRADE
  if [[ "${UPGRADE}" == "y" || "${UPGRADE}" == "Y" ]]; then
    echo "Upgrading existing release..."
    helm upgrade "${RELEASE}" "${HELM_CHART_PATH}" \
      --namespace "${NAMESPACE}" \
      --values "${VALUES_FILE}"
    INSTALL_OCCURRED=true
  else
    echo "Skipping installation."
  fi
else
  echo "MLflow Helm release not found. Installing..."
  helm install "${RELEASE}" "${HELM_CHART_PATH}" \
    --namespace "${NAMESPACE}" \
    --values "${VALUES_FILE}"
  INSTALL_OCCURRED=true
fi

if [[ "${INSTALL_OCCURRED}" == "true" && "${ENABLE_OAUTH_PROXY}" == "true" ]]; then
  echo "Setting up OpenShift OAuth proxy sidecar..."
  echo "Waiting for deployment to exist..."
  sleep 3

  # Patch deployment to add OAuth proxy sidecar
  oc patch deployment "${RELEASE}" -n "${NAMESPACE}" --type=json -p='[
    {"op": "add", "path": "/spec/template/spec/containers/-", "value": {
      "name": "oauth-proxy",
      "image": "registry.redhat.io/openshift4/ose-oauth-proxy:v4.12",
      "args": [
        "--https-address=:8444",
        "--upstream=https://localhost:8443",
        "--tls-cert=/etc/tls/private/tls.crt",
        "--tls-key=/etc/tls/private/tls.key",
        "--openshift-ca=/etc/pki/tls/certs/ca-bundle.crt",
        "--openshift-ca=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
        "--skip-auth-regex=^/health",
        "--openshift-sar={\"resource\":\"namespaces\",\"verb\":\"get\",\"resourceName\":\"'"${NAMESPACE}"'\",\"namespace\":\"'"${NAMESPACE}"'\"}",
        "--client-id=mlflow-oauth-'"${RELEASE}"'",
        "--redirect-url=https://'"${ROUTE_HOSTNAME}"'/oauth/callback",
        "--pass-access-token",
        "--cookie-secure=true"
      ],
      "env": [
        {"name": "OAUTH2_PROXY_CLIENT_SECRET", "valueFrom": {"secretKeyRef": {"name": "mlflow-oauth-'"${RELEASE}"'", "key": "client-secret"}}},
        {"name": "OAUTH2_PROXY_COOKIE_SECRET", "valueFrom": {"secretKeyRef": {"name": "mlflow-oauth-'"${RELEASE}"'", "key": "cookie-secret"}}}
      ],
      "ports": [
        {"name": "proxy-https", "containerPort": 8444}
      ],
      "volumeMounts": [
        {"name": "mlflow-tls", "mountPath": "/etc/tls/private", "readOnly": true}
      ],
      "resources": {
        "requests": {"cpu": "50m", "memory": "64Mi"},
        "limits": {"cpu": "200m", "memory": "256Mi"}
      }
    }}
  ]' || echo "WARNING: Failed to add OAuth proxy sidecar. You may need to add it manually."

  # Patch service to add OAuth proxy port
  oc patch service "${RELEASE}" -n "${NAMESPACE}" --type=json -p='[
    {"op": "add", "path": "/spec/ports/-", "value": {
      "name": "proxy-https",
      "protocol": "TCP",
      "port": 8444,
      "targetPort": "proxy-https"
    }}
  ]' || echo "WARNING: Failed to add OAuth proxy port to service. You may need to add it manually."

  echo "OAuth proxy setup complete."
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

if [[ "${ENABLE_OAUTH_PROXY}" == "true" ]]; then
  ROUTE_TARGET_PORT="proxy-https"
  ROUTE_TLS_TERMINATION="reencrypt"
else
  ROUTE_TARGET_PORT="https"
  ROUTE_TLS_TERMINATION="passthrough"
fi

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
    targetPort: ${ROUTE_TARGET_PORT}
  tls:
    termination: ${ROUTE_TLS_TERMINATION}
EOF

if oc get route "${RELEASE}" -n "${NAMESPACE}" &>/dev/null; then
  echo "Route '${RELEASE}' already exists. Updating..."
  oc apply -n "${NAMESPACE}" -f mlflow_route.yaml
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
echo "Authentication: $([ -z "${MLFLOW_APP_NAME}" ] && echo 'Disabled (direct browser access)' || echo 'Enabled (OpenShift OAuth proxy)')"
echo ""
echo "Check pod status:"
echo "  oc get pods -n ${NAMESPACE} -l component=mlflow"
echo ""
echo "View logs:"
echo "  oc logs -n ${NAMESPACE} -l component=mlflow"
echo ""
if [[ "${ENABLE_OAUTH_PROXY}" == "true" ]]; then
echo "View OAuth proxy logs:"
echo "  oc logs -n ${NAMESPACE} deployment/${RELEASE} -c oauth-proxy"
echo ""
fi
echo "Add more namespaces as MLflow workspaces:"
echo "  oc label namespace <target-namespace> mlflow-enabled=true"
echo ""
echo "Uninstall MLflow:"
echo "  helm uninstall ${RELEASE} -n ${NAMESPACE}"
echo "  oc delete route ${RELEASE} -n ${NAMESPACE}"
echo "  oc delete OAuthClient mlflow-oauth-${RELEASE}"
echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="