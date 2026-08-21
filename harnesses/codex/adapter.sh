#!/usr/bin/env bash
# harnesses/codex/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"

cd "$WORKDIR"
codex exec \
    $MODEL_FLAG \
    --json \
    --skip-git-repo-check \
    --sandbox danger-full-access \
    - < "$PROMPT_FILE" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
