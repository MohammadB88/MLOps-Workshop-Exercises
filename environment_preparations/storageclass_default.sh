#!/usr/bin/env bash
set -euo pipefail

############################################
# Set Default StorageClass on OpenShift
# Lists available StorageClasses, lets the
# user pick one, sets it as the cluster
# default, and prints proof of the change.
############################################

echo "=========================================="
echo " OpenShift Default StorageClass Selector"
echo "=========================================="

############################################
# Check prerequisites
############################################
if ! command -v oc &>/dev/null; then
  echo "ERROR: oc (OpenShift CLI) is not installed. Please install oc first."
  exit 1
fi

if ! oc whoami &>/dev/null; then
  echo "ERROR: Not logged in to an OpenShift cluster. Run 'oc login' first."
  exit 1
fi

############################################
# 1. Discover available StorageClasses
############################################
echo ""
echo "[1/3] Discovering available StorageClasses..."

if ! SC_OUTPUT=$(oc get storageclass -o name 2>/dev/null) || [[ -z "${SC_OUTPUT}" ]]; then
  echo "ERROR: No StorageClasses found on this cluster."
  exit 1
fi

mapfile -t SC_LIST < <(echo "${SC_OUTPUT}" | sed 's|storageclass.storage.k8s.io/||')

echo ""
echo "Available StorageClasses:"
for i in "${!SC_LIST[@]}"; do
  IS_DEFAULT=$(oc get storageclass "${SC_LIST[$i]}" -o jsonpath='{.metadata.annotations.storageclass\.kubernetes\.io/is-default-class}' 2>/dev/null)
  PROVISIONER=$(oc get storageclass "${SC_LIST[$i]}" -o jsonpath='{.provisioner}' 2>/dev/null)
  DEFAULT_LABEL=""
  [[ "${IS_DEFAULT}" == "true" ]] && DEFAULT_LABEL=" (current default)"
  echo "  $((i+1))) ${SC_LIST[$i]} [provisioner: ${PROVISIONER}]${DEFAULT_LABEL}"
done

############################################
# 2. Prompt user to choose
############################################
echo ""
read -p "Select the StorageClass to set as default (number): " SC_CHOICE

if [[ ! "${SC_CHOICE}" =~ ^[0-9]+$ ]] || (( SC_CHOICE < 1 || SC_CHOICE > ${#SC_LIST[@]} )); then
  echo "ERROR: Invalid selection."
  exit 1
fi

TARGET_SC="${SC_LIST[$((SC_CHOICE-1))]}"
echo "Selected StorageClass: ${TARGET_SC}"

read -p "Set '${TARGET_SC}' as the cluster default StorageClass? (y/n): " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
  echo "Cancelled."
  exit 0
fi

############################################
# 3. Apply default annotation
############################################
echo ""
echo "[2/3] Updating StorageClass annotations..."

for SC in "${SC_LIST[@]}"; do
  if [[ "${SC}" == "${TARGET_SC}" ]]; then
    continue
  fi
  CURRENT_DEFAULT=$(oc get storageclass "${SC}" -o jsonpath='{.metadata.annotations.storageclass\.kubernetes\.io/is-default-class}' 2>/dev/null)
  if [[ "${CURRENT_DEFAULT}" == "true" ]]; then
    echo "  Unsetting previous default: ${SC}"
    oc patch storageclass "${SC}" \
      -p '{"metadata": {"annotations": {"storageclass.kubernetes.io/is-default-class": "false"}}}'
  fi
done

echo "  Setting new default: ${TARGET_SC}"
oc patch storageclass "${TARGET_SC}" \
  -p '{"metadata": {"annotations": {"storageclass.kubernetes.io/is-default-class": "true"}}}'

############################################
# 4. Proof of configuration
############################################
echo ""
echo "[3/3] Proof of configuration"
echo "=========================================="
echo ""
echo "StorageClass list (DEFAULT column reflects the change):"
oc get storageclass
echo ""
echo "Annotation on '${TARGET_SC}':"
oc get storageclass "${TARGET_SC}" \
  -o jsonpath='{.metadata.name}{"\t"}{.metadata.annotations.storageclass\.kubernetes\.io/is-default-class}{"\n"}'
echo ""
echo "=========================================="
echo "Default StorageClass set to '${TARGET_SC}'."
echo "=========================================="
