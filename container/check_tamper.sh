#!/usr/bin/env bash
# container/check_tamper.sh
# Checks if the agent modified any test files.
# Usage: check_tamper.sh <workdir> <test_files...>
# Exit 0 = no tamper, exit 1 = tampered
set -euo pipefail

WORKDIR="$1"
shift
TEST_FILES=("$@")

cd "$WORKDIR"

for tf in "${TEST_FILES[@]}"; do
    if git diff --quiet -- "$tf" 2>/dev/null; then
        :
    else
        echo "TAMPERED: $tf" >&2
        exit 1
    fi
done

exit 0
