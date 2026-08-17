#!/usr/bin/env bash
# harnesses/droid/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag (unused — model comes from settings.json)
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

cd "$WORKDIR"
droid exec "$PROMPT" \
    --output-format text \
    --skip-permissions-unsafe \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
