#!/usr/bin/env bash
# harnesses/copilot/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

# entrypoint exports API_KEY and MODEL_URL (already overridden to the proxy)
export COPILOT_PROVIDER_TYPE="openai"
export COPILOT_PROVIDER_BASE_URL="$MODEL_URL"
export COPILOT_PROVIDER_API_KEY="$API_KEY"

cd "$WORKDIR"
copilot -p "$PROMPT" \
    $MODEL_FLAG \
    --allow-all-tools \
    --allow-all-paths \
    --output-format json \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
