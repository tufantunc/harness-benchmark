#!/usr/bin/env bash
# harnesses/junie/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

junie --skip-update-check \
    $MODEL_FLAG \
    --project "$WORKDIR" \
    --output-format json \
    --task "$PROMPT" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
