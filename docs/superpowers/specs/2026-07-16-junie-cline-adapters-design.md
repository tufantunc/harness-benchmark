# Junie + Cline Adapters — Design Spec

**Date:** 2026-07-16
**Status:** Approved
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add JetBrains Junie CLI and Cline CLI as fourth and fifth harnesses, extending the benchmark to a five-harness comparison (opencode vs pi vs grok vs junie vs cline) with the same LLM.

## Scope

- Create `harnesses/junie/` adapter (manifest + adapter.sh)
- Create `harnesses/cline/` adapter (manifest + adapter.sh)
- Add `parse_junie_events` + `parse_cline_events` to `container/extract_metrics.py`
- Update `docker/Dockerfile` to install both via npm
- Update `benchmark.yaml` harnesses list

## No Changes Needed

entrypoint.sh, store.py, report.py, runner.py — all harness-count-agnostic.

## Junie CLI

| Property | Value |
|----------|-------|
| Install | `npm install -g @jetbrains/junie` |
| Headless | `junie --task "prompt" --output-format json --json-output-file <path>` |
| Config | `.junie/models/<name>.json` (JSON model profile) |
| Custom endpoint | `baseUrl` (full URL), `apiType: "OpenAICompletion"`, `apiKey: "${ENV_VAR}"` |
| Model selection | `--model custom:<profile-name>` |
| Docs | https://junie.jetbrains.com/docs/custom-llm-models.html |

### Setup hook

Creates `$WORKDIR/.junie/models/benchmark.json` with the proxy URL as baseUrl. Junie's baseUrl is the **complete endpoint URL** (no path appended), so `/chat/completions` is included.

### Adapter invocation

```bash
junie --skip-update-check --model custom:benchmark --project "$WORKDIR" \
    --output-format json --json-output-file /output/events.jsonl "$PROMPT"
```

## Cline CLI

| Property | Value |
|----------|-------|
| Install | `npm install -g cline` |
| Headless | `cline "prompt" --json --auto-approve true` |
| Config | `~/.cline/data/settings/providers.json` |
| Custom endpoint | OpenAI provider with custom `baseUrl` field |
| Model selection | `-P openai -m <model>` or `--provider openai --model <model>` |
| API key | `-k <key>` flag or stored in providers.json |
| Docs | https://docs.cline.bot/cli/cli-reference |

### Setup hook

Creates `~/.cline/data/settings/providers.json` configuring the OpenAI provider with proxy URL as baseUrl. The adapter also passes `-k "$API_KEY"` as a runtime override.

### Adapter invocation

```bash
cline "$PROMPT" --json --auto-approve true -P openai -m "$MODEL_NAME" \
    -c "$WORKDIR" -k "$API_KEY"
```

## Metric Parsers

Both are best-effort parsers using the shared `_iter_events` + `_accumulate_usage` helpers. Token/cost data comes from the logging proxy (authoritative source at API boundary).

- `parse_junie_events`: Junie outputs JSON to `--json-output-file`. Event types TBD from real capture.
- `parse_cline_events`: Cline `--json` outputs `{"type":"say","text":"...","ts":...}`. No usage in events; proxy is sole source.

## Design Decisions

1. **Junie baseUrl includes path**: Unlike other adapters where baseUrl is the API root, Junie requires the full endpoint URL. The setup hook appends `/chat/completions`.

2. **Cline uses runtime key override**: `-k "$API_KEY"` passed at runtime instead of storing key in providers.json, avoiding writing secrets to disk.

3. **Both parsers are best-effort**: Real event fixtures should be captured from actual runs and used to calibrate the parsers. Until then, the logging proxy provides authoritative token/cost data.
