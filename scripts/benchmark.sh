#!/usr/bin/env bash
# scripts/benchmark.sh — main entry point
# Loads .env, ensures prerequisites, runs the benchmark.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Load .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Ensure polyglot-benchmark is initialized
./scripts/setup-polyglot.sh

# Ensure venv
if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
fi

# Run benchmark via Python
.venv/bin/python -m benchmark "$@"
