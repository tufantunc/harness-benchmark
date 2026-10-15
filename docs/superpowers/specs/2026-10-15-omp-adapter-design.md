# oh-my-pi (omp) Harness Adapter — Design Spec

**Date:** 2026-10-15
**Status:** Approved (adapter prep; campaign queued)
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add oh-my-pi (`omp`, can1357/oh-my-pi — a pi fork with a Rust core, MIT) as
harness 14. Evaluation found the cleanest provider story since pi itself:
pi-shaped config files plus a pinned-binary install path with no installer
drift exposure.

## Harness Details

| Property | Value |
|----------|-------|
| Install | pinned release binary: `omp-linux-arm64` @ v18.11.0 (GitHub asset, SHA256-verified via release digest) |
| Config | `~/.omp/agent/models.yml` (providers) + `~/.omp/agent/config.yml` (modelRoles) |
| API protocol | `api: openai-completions` (OpenAI-compatible) |
| API key | embedded in models.yml (crush precedent) |
| Headless | `omp -p "<prompt>"` — one-shot, exits |
| Model selection | `--model benchmark/<model>` flag; also preset via `modelRoles.default` |
| License | MIT (vendored parts keep upstream licenses) |

### Setup hook writes

```yaml
# ~/.omp/agent/models.yml
providers:
  benchmark:
    baseUrl: "<MODEL_URL>"          # proxy (127.0.0.1:8080)
    api: openai-completions
    apiKey: "<API_KEY>"
    models:
      - id: "<MODEL_NAME>"
        contextWindow: 1048576
        maxTokens: 131072
```

```yaml
# ~/.omp/agent/config.yml
modelRoles:
  default: benchmark/<MODEL_NAME>
```

pi-fork shapes (same as our pi adapter's models.json, YAML-flavored).

### Invocation

```bash
omp -p "$PROMPT" --model benchmark/$MODEL_NAME > /output/events.jsonl
```

`-p` output format is the one unknown; resolved empirically by the real-key
verification run (rpc mode's NDJSON is documented, plain -p is not). The
proxy captures tokens regardless; the parser is written from the captured
schema (established methodology).

## Registration

- `docker/Dockerfile`: pinned binary download block (curl + sha256sum -c + chmod)
- `benchmark.yaml` harnesses list append (`omp`)

## Verification

Real-key rep-98 first; success = request_count > 0, served_model populated,
schema captured. Then parser (TDD), suite, review-pro, campaign.
