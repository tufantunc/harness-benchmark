#!/usr/bin/env bash
# container/run_tests.sh
# Runs the exercise test suite by language.
# Usage: run_tests.sh <language> <workdir> <test_files...>
# Output: test stdout+stderr to stdout, exit code = test exit code
set -euo pipefail

LANGUAGE="$1"
WORKDIR="$2"
shift 2
TEST_FILES=("$@")

cd "$WORKDIR"

case "$LANGUAGE" in
    python)
        for tf in "${TEST_FILES[@]}"; do
            python3 -m pytest "$tf" --tb=short -q
        done
        ;;
    javascript)
        npm run test 2>&1
        ;;
    *)
        echo "Unknown language: $LANGUAGE" >&2
        exit 1
        ;;
esac
