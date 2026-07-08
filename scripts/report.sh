#!/usr/bin/env bash
# scripts/report.sh — generate report only (no benchmark run)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
fi

.venv/bin/python -m benchmark --report-only "$@"
