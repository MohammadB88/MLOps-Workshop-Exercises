#!/bin/bash
# Build and push Docker image for LLM serving

set -euo pipefail

# Default variables - override via environment or CLI
IMAGE_NAME="${IMAGE_NAME:-llm-instruction-tuning}"
VERSION="${VERSION:-v1.0.0}"
REGISTRY="${REGISTRY:-quay.io}"
NAMESPACE="${NAMESPACE:-your-namespace}"

usage() {
    echo "Usage: $0 [--name IMAGE_NAME] [--version VERSION] [--registry REGISTRY] [--namespace NAMESPACE]"
    echo ""
    echo "Build and push the LLM serving Docker image."
    echo "  --name       Image name (default: llm-instruction-tuning)"
    echo "  --version    Image tag (default: v1.0.0)"
    echo "  --registry   Container registry (default: quay.io)"
    echo "  --namespace  Registry namespace (default: your-namespace)"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name) IMAGE_NAME="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --registry) REGISTRY="$2"; shift 2 ;;
        --namespace) NAMESPACE="$2"; shift 2 ;;
        *) usage ;;
    esac
done

# Full image tag
FULL_TAG="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${VERSION}"

echo "Building image: ${FULL_TAG}"

# Build the image
docker build -t "${FULL_TAG}" .

echo "Image built successfully: ${FULL_TAG}"
echo ""
echo "To push to registry:"
echo "  docker push ${FULL_TAG}"
echo ""
echo "To run locally:"
echo "  docker run --gpus all -p 8000:8000 ${FULL_TAG}"
