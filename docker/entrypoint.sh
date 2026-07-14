#!/usr/bin/env bash
# docker/entrypoint.sh
# Container-internal orchestrator for a single (harness x exercise x rep).
#
# Usage: entrypoint.sh <harness> <exercise_relpath> <rep> <results_dir>
# Env:   MODEL_URL, PROTOCOL, MODEL_NAME, LLM_API_KEY (or $api_key_env), TASK_TIMEOUT
set -euo pipefail

HARNESS="$1"
EXERCISE_REL="$2"
REP="$3"
RESULTS_DIR="$4"

POLYGLOT="/app/polyglot-benchmark"
EXERCISE_SRC="$POLYGLOT/$EXERCISE_REL"
WORKDIR="/workdir"
OUTPUT="/output"

mkdir -p "$WORKDIR" "$OUTPUT"
cd "$WORKDIR"
git init -q 2>/dev/null || true
git add -A && git commit -q -m "init" --allow-empty 2>/dev/null || true

# --- 1. SETUP: copy exercise stub (no test files) ---
CONFIG_JSON="$EXERCISE_SRC/.meta/config.json"
SOLUTION_FILES=$(jq -r '.files.solution[]' "$CONFIG_JSON")
TEST_FILES=$(jq -r '.files.test[]' "$CONFIG_JSON")

for f in $SOLUTION_FILES; do
    mkdir -p "$(dirname "$WORKDIR/$f")"
    cp "$EXERCISE_SRC/$f" "$WORKDIR/$f"
done

cp -r "$EXERCISE_SRC/.docs" "$WORKDIR/.docs"

mkdir -p "$WORKDIR/.meta"
cp "$CONFIG_JSON" "$WORKDIR/.meta/config.json"

LANGUAGE=$(echo "$EXERCISE_REL" | cut -d/ -f1)
if [ "$LANGUAGE" = "javascript" ]; then
    for f in package.json babel.config.js .eslintrc .npmrc; do
        [ -f "$EXERCISE_SRC/$f" ] && cp "$EXERCISE_SRC/$f" "$WORKDIR/$f"
    done
fi

git add -A && git commit -q -m "exercise setup" 2>/dev/null || true

# --- 2. START PROXY + SETUP HOOK ---
HARNESS_DIR="/app/harnesses/$HARNESS"
MANIFEST="$HARNESS_DIR/manifest.yaml"

export PROTOCOL MODEL_NAME
export API_KEY="${LLM_API_KEY:-}"

# Start logging proxy (transparent to agent: agent → proxy → real API)
REAL_MODEL_URL="${MODEL_URL:-}"
export UPSTREAM_URL="$REAL_MODEL_URL"
export CAPTURE_DIR="$OUTPUT/captured-payloads"
export PROXY_PORT=8080
node /app/container/proxy.js > "$OUTPUT/proxy.log" 2>&1 &
PROXY_PID=$!
sleep 1

# Override MODEL_URL to proxy so setup hook generates config pointing at proxy
export MODEL_URL="http://127.0.0.1:${PROXY_PORT}"

SETUP_SCRIPT=$(jq -r '.setup // empty' "$MANIFEST" 2>/dev/null || true)
if [ -n "$SETUP_SCRIPT" ]; then
    eval "$SETUP_SCRIPT"
fi

# --- 3. PROMPT ASSEMBLE ---
ADDENDUM_FILE="/tmp/addendum.txt"
echo "Modify only the supplied files. Don't rename functions or classes. Only use standard libraries. Don't install packages." > "$ADDENDUM_FILE"
/app/container/assemble_prompt.sh "$WORKDIR" "$WORKDIR/prompt.txt" "$ADDENDUM_FILE"

# --- 4. AGENT INVOKE ---
MODEL_FLAG=$(jq -r '.invoke.model_flag // "--model benchmark/$MODEL_NAME"' "$MANIFEST" 2>/dev/null || echo "--model benchmark/\$MODEL_NAME")
MODEL_FLAG=$(eval echo "$MODEL_FLAG")

ADAPTER="$HARNESS_DIR/adapter.sh"
START_TIME=$(date +%s)

set +e
timeout "${TASK_TIMEOUT:-600}" "$ADAPTER" "$WORKDIR/prompt.txt" "$WORKDIR" "$MODEL_FLAG" \
    > "$OUTPUT/events.jsonl" 2> "$OUTPUT/agent-stderr.log"
AGENT_EXIT=$?
set -e

END_TIME=$(date +%s)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
TIMED_OUT=0
if [ "$AGENT_EXIT" = 124 ]; then
    TIMED_OUT=1
fi

# Kill proxy + analyze captured payloads
kill "$PROXY_PID" 2>/dev/null || true
wait "$PROXY_PID" 2>/dev/null || true

node /app/container/analyze-proxy.js "$OUTPUT/captured-payloads" > "$OUTPUT/proxy-analysis.json" 2>/dev/null || \
    echo '{"cache_write_tokens":0,"cache_read_tokens":0,"system_prompt_tokens":0,"tool_schema_tokens":0,"prefix_stable":true,"prefix_variants":0,"request_count":0}' > "$OUTPUT/proxy-analysis.json"

# --- 5. TEST RUN: copy test files, run suite ---
for f in $TEST_FILES; do
    mkdir -p "$(dirname "$WORKDIR/$f")"
    cp "$EXERCISE_SRC/$f" "$WORKDIR/$f"
done

set +e
/app/container/run_tests.sh "$LANGUAGE" "$WORKDIR" $TEST_FILES > "$OUTPUT/test-output.txt" 2>&1
TEST_EXIT=$?
set -e

# --- 6. COLLECT ---
git diff --no-color > "$OUTPUT/diff.patch" 2>/dev/null || true
DIFF_LOC=$(git diff --shortstat 2>/dev/null | grep -oP '\d+(?= insertion)' || echo "0")

set +e
/app/container/check_tamper.sh "$WORKDIR" $TEST_FILES > "$OUTPUT/tamper-check.txt" 2>&1
TAMPER_EXIT=$?
set -e
TAMPERED=$([ "$TAMPER_EXIT" = "1" ] && echo "true" || echo "false")

METRIC_FORMAT=$(jq -r '.metric_format // "pi"' "$MANIFEST" 2>/dev/null || echo "pi")
python3 /app/container/extract_metrics.py "$OUTPUT/events.jsonl" "$METRIC_FORMAT" "$OUTPUT/parsed-metrics.json" 2>/dev/null || \
    echo '{"tokens_input":0,"tokens_output":0,"tokens_cached":0,"cost_usd":0.0,"tool_calls":0,"llm_calls":0}' > "$OUTPUT/parsed-metrics.json"

# --- 7. EMIT metrics.json to stdout ---
EXERCISE_NAME=$(basename "$EXERCISE_REL")
python3 -c "
import json
parsed = json.load(open('$OUTPUT/parsed-metrics.json'))
proxy = json.load(open('$OUTPUT/proxy-analysis.json'))
result = {
    'harness': '$HARNESS',
    'model': '$MODEL_NAME',
    'language': '$LANGUAGE',
    'exercise': '$EXERCISE_NAME',
    'repetition': $REP,
    'success': $( [ "$TEST_EXIT" = "0" ] && [ "$TAMPER_EXIT" = "0" ] && echo "True" || echo "False" ),
    'test_exit_code': $TEST_EXIT,
    'agent_exit_code': $AGENT_EXIT,
    'timed_out': $TIMED_OUT,
    'tampered': $TAMPERED,
    'tokens_input': parsed.get('tokens_input', 0),
    'tokens_output': parsed.get('tokens_output', 0),
    'tokens_cached': parsed.get('tokens_cached', 0),
    'cost_usd': parsed.get('cost_usd', 0.0),
    'tool_calls': parsed.get('tool_calls', 0),
    'llm_calls': parsed.get('llm_calls', 0),
    'duration_sec': $DURATION,
    'diff_loc': $DIFF_LOC,
    'cache_write_tokens': proxy.get('cache_write_tokens', 0),
    'cache_read_tokens': proxy.get('cache_read_tokens', 0),
    'system_prompt_tokens': proxy.get('system_prompt_tokens', 0),
    'tool_schema_tokens': proxy.get('tool_schema_tokens', 0),
    'prefix_stable': proxy.get('prefix_stable', True),
    'prefix_variants': proxy.get('prefix_variants', 0),
    'request_count': proxy.get('request_count', 0),
}
print(json.dumps(result))
"

# --- 8. Copy artifacts to mounted volume ---
ARTIFACT_DIR="$RESULTS_DIR/artifacts/$HARNESS/$LANGUAGE/$EXERCISE_NAME/rep-$REP"
mkdir -p "$ARTIFACT_DIR"
cp -r "$OUTPUT/"* "$ARTIFACT_DIR/" 2>/dev/null || true
