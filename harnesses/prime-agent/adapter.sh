#!/usr/bin/env bash
# harnesses/prime-agent/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
# -p (print mode) runs in-process, without the background daemon.
# No --offline: the Python skills (edit, goal, refine, …) are uv-installed
# into the kernel venv at session start, and --offline cancels that install
# ("Python skill edit failed to install and will be unavailable"). Online it
# takes ~1.5s per run; installing them at image build did not stick.
# message_update events are dropped: each carries a snapshot of the whole
# message so far (one real task wrote 51 MB, 99.7% of it these lines), and
# the parser reads only message_end and tool_execution_start. Line-buffered
# so a timeout kill does not lose grep's pending output.
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
    < /dev/null 2>/output/agent-stderr.log \
    | { grep --line-buffered -v '^{"type":"message_update"' || true; } > /output/events.jsonl

echo $? > /output/agent-exit-code
