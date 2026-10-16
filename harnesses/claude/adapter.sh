#!/usr/bin/env bash
# harnesses/claude/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

# entrypoint exports API_KEY and MODEL_URL (the proxy; upstream overridden
# per-manifest to the Anthropic-compatible endpoint)
export ANTHROPIC_BASE_URL="$MODEL_URL"
export ANTHROPIC_AUTH_TOKEN="$API_KEY"
export ANTHROPIC_MODEL="$MODEL_NAME"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
# The benchmark container IS our sandbox — this declares it so
# --dangerously-skip-permissions is allowed under the container's root user.
export IS_SANDBOX=1

cd "$WORKDIR"
claude -p "$PROMPT" \
    --output-format stream-json \
    --verbose \
    --dangerously-skip-permissions \
    $MODEL_FLAG \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
