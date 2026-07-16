# Grok Build Adapter — Design Spec

**Date:** 2026-07-16
**Status:** Approved
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add xAI's Grok Build as a third harness to the benchmark, enabling triple comparison (opencode vs pi vs grok) with the same LLM, same tasks, same isolation.

## Scope

- Create `harnesses/grok/` adapter (manifest + adapter.sh)
- Add Grok-specific metric parser to `container/extract_metrics.py`
- Update `docker/Dockerfile` to install Grok Build via curl installer
- Update `benchmark.yaml` harnesses list to include `grok`

## No Changes Needed

- `docker/entrypoint.sh` — proxy + setup hook pattern is harness-agnostic
- `benchmark/store.py` — no new columns
- `benchmark/report.py` — already supports arbitrary number of harnesses
- `benchmark/runner.py` — iterates over config.harnesses dynamically

## Grok Build Details

| Property | Value |
|----------|-------|
| Install | `curl -fsSL https://x.ai/cli/install.sh \| bash` (not npm) |
| Headless | `grok -p "$PROMPT" --output-format streaming-json --always-approve -m <model> --cwd <dir>` |
| Config | `~/.grok/config.toml` (TOML, not JSON/YAML) |
| Custom model | `[model.benchmark]` section with `model`, `base_url`, `env_key` |
| Output | `streaming-json` = newline-delimited JSON events |
| CI mode | `--no-auto-update` skips update checks |
| Docs | https://docs.x.ai/build/overview |

## Adapter Design

### manifest.yaml

Setup hook generates `~/.grok/config.toml` with:
- `base_url` pointing to the proxy URL (`$MODEL_URL` already overridden to proxy by entrypoint)
- `env_key = "LLM_API_KEY"` (the env var name holding the API key)
- Model name from `$MODEL_NAME`

### adapter.sh

Invokes grok in headless streaming-json mode with `--always-approve` (auto-approve tools, no prompts) and `--no-auto-update` (skip update checks).

### Metric Parser

`parse_grok_events()` in `extract_metrics.py` — best-effort parser for tool_calls/llm_calls from streaming-json events. Token/cost data comes from the logging proxy (authoritative source at API boundary), not the event stream.

## Design Decisions

1. **TOML config via `cat <<EOF`**: Grok uses TOML, not JSON. The setup hook uses a heredoc to write the config file, same pattern as opencode (JSON) and pi (JSON) but different format.

2. **Proxy is primary metric source**: Grok's streaming-json event format is not fully documented for usage/token fields. The logging proxy captures usage from API responses regardless, so token/cost data is reliable. The event parser provides best-effort tool_call/llm_call counts.

3. **curl installer in Dockerfile**: Grok Build is not on npm. The Dockerfile adds a `RUN curl -fsSL https://x.ai/cli/install.sh | bash` line. The install script places the binary in the PATH.
