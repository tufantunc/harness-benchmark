#!/usr/bin/env bash
# harnesses/_template/adapter.sh
# Invoked by entrypoint.sh with: $1=prompt-file  $2=workdir  $3=model-flag
# Must write JSON events to /output/events.jsonl and exit.
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

your-harness run "$PROMPT" \
    $MODEL_FLAG \
    --workdir "$WORKDIR" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
