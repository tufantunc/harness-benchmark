#!/usr/bin/env bash
# harnesses/grok/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

grok --no-auto-update -p "$PROMPT" \
    --output-format streaming-json \
    --always-approve \
    $MODEL_FLAG \
    --cwd "$WORKDIR" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
