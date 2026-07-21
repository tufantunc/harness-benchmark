#!/usr/bin/env bash
# harnesses/cline/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

cd "$WORKDIR"
cline "$PROMPT" \
    --json \
    --auto-approve true \
    -P openai \
    $MODEL_FLAG \
    -c "$WORKDIR" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
