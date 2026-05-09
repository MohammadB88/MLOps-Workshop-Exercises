#!/usr/bin/env bash
set -euo pipefail

############################################
# Install Helm (if not present)
############################################
echo "Checking Helm installation..."

if ! command -v helm &>/dev/null; then
  echo "Helm not found. Installing Helm..."

  curl -fsSL -o get_helm.sh \
    https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4

  chmod 700 get_helm.sh
  ./get_helm.sh

  rm -f get_helm.sh
  echo "Helm installed successfully."
else
  echo "Helm already installed. Version:"
  helm version --short
fi