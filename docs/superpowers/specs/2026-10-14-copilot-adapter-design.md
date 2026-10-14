# GitHub Copilot CLI Harness Adapter — Design Spec

**Date:** 2026-10-14
**Status:** Approved (adapter prep; campaign queued)
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add GitHub Copilot CLI (`@github/copilot`) as harness 13, extending the
benchmark's glm-5.3 cohort. Notable because the account wall that blocked
qoder/fx/droid is explicitly absent: `copilot help providers` states
"GitHub authentication is not required when using a custom provider", and
BYOK is activated purely by environment variables — verified empirically
(no-login dead-endpoint probe reached the network layer).

## Harness Details

| Property | Value |
|----------|-------|
| Install | `npm install -g @github/copilot` (v1.0.97) |
| Config | none — `COPILOT_PROVIDER_*` env vars (BYOK) |
| API protocol | OpenAI-compatible (`COPILOT_PROVIDER_TYPE=openai`, `WIRE_API=completions` default) |
| API key | env `COPILOT_PROVIDER_API_KEY` |
| Headless | `copilot -p "<prompt>"` (exits after completion) |
| Full-auto | `--allow-all-tools` (required for -p) + `--allow-all-paths` |
| Output | `--output-format json` (JSONL, one JSON object per line) |
| Model selection | `--model <model-id>` |
| Docs | `copilot help providers` (in-CLI, authoritative) |

### adapter.sh env wiring (qwen pattern)

```bash
export COPILOT_PROVIDER_TYPE="openai"      # OpenAI-compatible
export COPILOT_PROVIDER_BASE_URL="$MODEL_URL"  # proxy (127.0.0.1:8080)
export COPILOT_PROVIDER_API_KEY="$API_KEY"
```

`WIRE_API` stays default (`completions` — chat). `$HOME/.copilot/providers.json`
would override the env vars — the benchmark container has none (noted guard).
GitHub-side features (`/delegate`) requiring sign-in are irrelevant here.

### Invocation

```bash
copilot -p "$PROMPT" --model "$MODEL_NAME" \
    --allow-all-tools --allow-all-paths --no-auto-update --output-format json \
    > /output/events.jsonl
```

`--no-auto-update` matters: self-update defaults to ON (verified in the
binary — disabled only via this flag or `COPILOT_AUTO_UPDATE=false`),
which would allow runtime code swaps inside benchmark containers.

## Verification methodology

Real-key single-run first (rep-98) — path correctness cannot be validated
with dummy keys (auth precedes routing upstream). Success criteria: run
completes, `request_count > 0`, `served_model` populated (expect glm-5.3),
real JSONL event schema captured for the parser. Watch for: first-run
trusted-directory prompt behavior in headless mode (empirically checked
in the verification run).

## Metric Parser

Bespoke, written AFTER the real-key run captures the actual `--output-format
json` event schema (codex/qwen/dsh lesson: never guess schemas). Token/cost
data comes from the proxy (authoritative); parser counts tool/llm events.

## Registration

- `docker/Dockerfile` npm block: `npm install -g @github/copilot`
- `benchmark.yaml` harnesses list append (`copilot`)
