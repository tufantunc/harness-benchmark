#!/usr/bin/env bash
# scripts/setup-polyglot.sh — ensure polyglot-benchmark submodule is initialized
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

if [ ! -d polyglot-benchmark/python/exercises/practice ] || [ -z "$(ls -A polyglot-benchmark/python/exercises/practice 2>/dev/null)" ]; then
    echo "Initializing polyglot-benchmark submodule..."
    git submodule update --init --recursive
fi

echo "polyglot-benchmark ready."
PYTHON_COUNT=$(find polyglot-benchmark/python/exercises/practice -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
JS_COUNT=$(find polyglot-benchmark/javascript/exercises/practice -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
echo "Python exercises: $PYTHON_COUNT"
echo "JavaScript exercises: $JS_COUNT"
