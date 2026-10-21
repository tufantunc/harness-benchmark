# WrongStack (wstack) Harness Adapter — Design Spec

**Date:** 2026-10-22
**Status:** Approved (adapter prep; campaign queued)
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add WrongStack (`wstack`, WrongStack/WrongStack — MIT, self-contained harness
with its own agent runtime, not an orchestrator of other CLIs) as harness 16.

## Verified facts (2026-10-22 probes)

- Release binaries + official SHA256SUMS → omp-style pinned install, no
  installer drift (v1.1.12, wstack-linux-arm64)
- one-shot = **positional task** (`wstack "<task>"` runs and exits); in 1.1.12 `-p` starts a REPL instead (docs lag the binary — found empirically)
- `--output-format stream-json` — "init, assistant, tool_result, result
  lines" (clean parser schema; `--include-partial-messages` left off)
- `--yolo-plus` — never ask for anything (explicit deny rules still refuse)
- Exit codes documented: 0 done, 1 failed/limit/budget/schema, 130 aborted
- Custom provider: `~/.wrongstack/profiles/<name>/config.json` →
  `providers.<id> {type: "openai-compatible", family, baseUrl, apiKey,
  models[]}` (crush/pi config-file pattern); keys auto-encrypted on the CLI
  side — fresh per-run container config is the expected flow
- `--provider`/`--model` flags skip the startup picker (headless-safe)

## Setup hook writes (~/.wrongstack/profiles/default/config.json)

```json
{
  "provider": "benchmark",
  "model": "<MODEL_NAME>",
  "providers": {
    "benchmark": {
      "type": "openai-compatible",
      "family": "openai-compatible",
      "baseUrl": "<MODEL_URL>",
      "apiKey": "<API_KEY>",
      "models": [{ "id": "<MODEL_NAME>" }]
    }
  }
}
```

## Invocation

```bash
wstack "$PROMPT" --provider benchmark --yolo-plus \
    --output-format stream-json --no-models-refresh \
    $MODEL_FLAG > /output/events.jsonl
```

(model_flag: `--model $MODEL_NAME`)

## Empirical gates (rep-98, real key)

1. Default profile name is "default" (else: startup picker blocks headless)
2. Plaintext apiKey in config accepted + auto-encrypted on load
3. stream-json schema captured for the parser
4. Trust prompts do not block one-shot mode

## Registration

- `docker/Dockerfile`: pinned wstack-linux-arm64 v1.1.12 (SHA256SUMS hash)
- `benchmark.yaml` harnesses append (`wstack`)

## Metric parser

Bespoke, from the captured stream-json schema (established methodology);
token/cost via the proxy as authoritative.
