#!/usr/bin/env bash
# harnesses/prime-agent/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
# -p (print mode) runs in-process, without the background daemon.
# No --offline: the Python skills (edit, goal, refine, …) are uv-installed
# into the kernel venv at session start, and --offline cancels that install
# ("Python skill edit failed to install and will be unavailable"). Online it
# takes ~1.5s per run; installing them at image build did not stick.
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

export DO_NOT_TRACK=1

prime-agent \
    --mode json \
    --cwd "$WORKDIR" \
    --provider benchmark \
    $MODEL_FLAG \
    -p "$PROMPT" \
    < /dev/null \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
