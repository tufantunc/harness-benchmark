# Claude Code Harness Adapter — Design Spec

**Date:** 2026-10-16
**Status:** Approved (adapter prep; campaign queued)
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add Anthropic's Claude Code CLI (`@anthropic-ai/claude-code`) as harness 15.
Claude Code speaks the Anthropic Messages protocol; z.ai exposes an
Anthropic-compatible endpoint that accepts the coding-plan key, so the
benchmark's single-provider setup extends to it with one small
orchestrator addition: a per-harness proxy upstream override.

## Verified facts (2026-10-15 probes)

- `POST https://api.z.ai/api/anthropic/v1/messages` returns Anthropic
  Messages responses (`msg_...`, content blocks) with glm-5.3 requestable
- Both auth styles accepted: `x-api-key` (ANTHROPIC_API_KEY) and
  `Authorization: Bearer` (ANTHROPIC_AUTH_TOKEN)
- Proxy readiness: SSE usage extractor already has Anthropic
  message_start/message_delta branches; analyze-proxy reads the Anthropic
  `system` field; the duplicate-/v1 collapse does NOT trigger (the
  anthropic base URL does not end in a version segment)

## Harness Details

| Property | Value |
|----------|-------|
| Install | `npm install -g @anthropic-ai/claude-code` (version-pinned in Dockerfile) |
| Config | none — env vars only |
| Endpoint | `ANTHROPIC_BASE_URL` → the proxy (127.0.0.1:8080) |
| Auth | `ANTHROPIC_AUTH_TOKEN` = $API_KEY (Bearer; also accepted upstream) |
| Model | `--model glm-5.3` (explicit, for cohort consistency) + ANTHROPIC_MODEL |
| Headless | `claude -p "<prompt>"` — always uses env auth, no subscription prompt |
| Output | `--output-format stream-json` |
| Noise off | `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` (auto-update, telemetry, release notes) |
| Permissions | `--dangerously-skip-permissions` (container parity) |

## Orchestrator addition: per-harness proxy upstream

entrypoint.sh gains two lines: read optional manifest key `proxy_upstream`
(default `$MODEL_URL`) and export it as the proxy's `UPSTREAM_URL`. The
claude manifest sets `proxy_upstream: https://api.z.ai/api/anthropic` —
the proxy then forwards `/v1/messages` to
`/api/anthropic/v1/messages` unchanged. MODEL_URL (the adapter-facing
proxy address) is unaffected. Additive; no other harness changes behavior.

## adapter.sh wiring

```bash
export ANTHROPIC_BASE_URL="$MODEL_URL"        # the proxy
export ANTHROPIC_AUTH_TOKEN="$API_KEY"
export ANTHROPIC_MODEL="$MODEL_NAME"          # glm-5.3 via config
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
claude -p "$PROMPT" --output-format stream-json --dangerously-skip-permissions \
    $MODEL_FLAG > /output/events.jsonl
```

(model_flag: `--model $MODEL_NAME`; benchmark.yaml model name switched to
glm-5.3 at campaign time for cohort consistency — decided then.)

## Verification methodology

Real-key rep-98 first: expect request_count > 0, served_model = glm-5.3
(the anthropic endpoint echoes the requested model — check the response
payload to confirm actual serving), watch for onboarding/theme prompts in
headless mode. Parser written from the captured stream-json schema.

## Registration

- `docker/Dockerfile` npm block (pinned)
- `benchmark.yaml` harnesses append (`claude`)
