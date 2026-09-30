#!/usr/bin/env bash
# harnesses/qwen/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

# entrypoint exports API_KEY and MODEL_URL (already overridden to the proxy)
export OPENAI_API_KEY="$API_KEY"
export OPENAI_BASE_URL="$MODEL_URL"

cd "$WORKDIR"
qwen --auth-type openai --approval-mode yolo -o stream-json \
    $MODEL_FLAG \
    "$PROMPT" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
