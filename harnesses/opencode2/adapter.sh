#!/usr/bin/env bash
# harnesses/opencode2/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
# v2 dropped `run --dir` (cd instead) and defaults to a shared background
# service (--standalone gives each run a private server that exits with it).
# stdin is closed explicitly: v2 `run` hangs before the first request while
# stdin stays open.
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

cd "$WORKDIR"
opencode2 run \
    --standalone \
    --format json \
    --auto \
    $MODEL_FLAG \
    "$PROMPT" \
    < /dev/null \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
