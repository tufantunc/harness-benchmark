#!/usr/bin/env bash
# harnesses/whycodes/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag (unused — model comes from config.toml)
# --approve-tools: headless runs deny permission `ask` by default.
# WHYCODES_SANDBOX=off: the default bubblewrap sandbox is unavailable in the
# container (the fallback would warn and run on the host anyway).
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

export WHYCODES_SANDBOX=off

whycodes generate "$PROMPT" \
    -d "$WORKDIR" \
    --format stream-json \
    --approve-tools \
    < /dev/null \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
