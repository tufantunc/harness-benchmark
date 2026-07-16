#!/usr/bin/env bash
# harnesses/autohand/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

autohand -p "$PROMPT" \
    --yes \
    --unrestricted \
    $MODEL_FLAG \
    --path "$WORKDIR" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
