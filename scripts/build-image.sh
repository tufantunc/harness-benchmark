#!/usr/bin/env bash
# scripts/build-image.sh — build the Docker image
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

IMAGE_NAME="${HARNESS_IMAGE:-harness:latest}"

echo "Building Docker image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" -f docker/Dockerfile .

echo "Done: $IMAGE_NAME"
