# Qwen Code Harness Adapter — Design Spec

**Date:** 2026-09-30
**Status:** Approved (adapter prep; campaign queued after dsh + July re-runs)
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add Qwen Code (`@qwen-code/qwen-code`, QwenLM — a Gemini-CLI-derived coding
agent) as a new harness, extending the benchmark on the Z.ai endpoint.

## Harness Details

| Property | Value |
|----------|-------|
| Install | `npm install -g @qwen-code/qwen-code` (v0.24.7) |
| Config | `~/.qwen/settings.json` |
| Config format | JSON `modelProviders` map + `providerProtocol` + auth selection |
| API protocol | OpenAI-compatible (`wireApi: "chat-completions"`) |
| API key | Env var via `envKey` (not embedded) |
| Headless | positional prompt (one-shot; `-p` deprecated), `--approval-mode yolo` |
| Output | `-o stream-json` (NDJSON events) |
| Docs | repo `docs/users/configuration/model-providers.md` |

### Setup hook writes

**Revision during implementation:** the documented `modelProviders`
settings.json path crashes in 0.24.7 (`resolveModelConfig` TypeError —
verified against the bundled source; custom provider ids never resolve).
Working path is qwen's built-in `openai` auth type, which reads env vars
directly (`AUTH_ENV_MAPPINGS.openai`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`,
`OPENAI_MODEL`/`QWEN_MODEL`). adapter.sh exports them from the entrypoint's
`API_KEY`/`MODEL_URL` — no config file, no setup hook.

~~~json
{
  "modelProviders": { "benchmark": [ { "id": "<MODEL_NAME>",
    "envKey": "API_KEY", "baseUrl": "<MODEL_URL>",
    "wireApi": "chat-completions",
    "generationConfig": { "contextWindowSize": 1048576 } } ] },
  "providerProtocol": { "benchmark": "openai" },
  "security": { "auth": { "selectedType": "benchmark" } },
  "model": { "name": "<MODEL_NAME>" }
}
~~~
(The settings above are kept for reference — they are NOT written at runtime.)

### Invocation

```bash
OPENAI_API_KEY="$API_KEY" OPENAI_BASE_URL="$MODEL_URL" \
qwen --auth-type openai --approval-mode yolo -o stream-json \
    -m "$MODEL_NAME" "$PROMPT" > /output/events.jsonl
```

Flags verified against the installed CLI (`--help`): `--auth-type openai`,
`--approval-mode yolo`, `-o stream-json`, positional prompt, `-m`.

## Verification methodology

Real-key single-run first (rep-98), per the BigModel/Z.ai lessons: dummy-key
probes cannot validate paths (auth precedes routing) — see spec
`2026-08-21-codex-adapter-design.md` parking note. Success criteria: run
completes, `request_count > 0`, `served_model` populated (expect glm-5.3 on
the aliased endpoint), real event schema captured for the parser.

## Metric Parser

Bespoke or best-effort decided AFTER the real-key run captures the actual
`stream-json` event schema (codex lesson: never guess schemas). Token/cost
data comes from the proxy (authoritative); parser counts tool/llm events.

## Registration

- `docker/Dockerfile` npm block: `npm install -g @qwen-code/qwen-code`
- `benchmark.yaml` harnesses list append (`qwen`)

## Rejected alternative: atomic-agent

Evaluated same day: no one-shot prompt entry (`run` takes only `--cwd`, no
`-p`/`--model`); headless is a `serve` OpenAI-compatible server or an
undocumented Tauri sidecar protocol — both would need a custom driver layer
unlike all existing adapters. Revisit if a one-shot mode ships.
