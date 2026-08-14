# Four New Harness Adapters — Design Spec

**Date:** 2026-07-29
**Status:** Approved
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

## Overview

Add Factory Droid, Crush, Goose, and DeepSeek Harness (dsh) as harnesses 9-12, extending the benchmark to a twelve-harness comparison with the same LLM (GLM 5.2 via proxy).

## Scope

- Create `harnesses/{droid,crush,goose,dsh}/` adapters (manifest + adapter.sh)
- Add best-effort event parsers to `container/extract_metrics.py`
- Update `docker/Dockerfile` with install commands
- Update `benchmark.yaml` harness list
- Verify each harness with dummy-key container test; remove any that cannot connect through the proxy

## No Changes Needed

entrypoint.sh, store.py, report.py, runner.py, dashboard — all harness-count-agnostic.

## Harness Details

### Factory Droid

| Property | Value |
|----------|-------|
| Install | `curl -fsSL https://app.factory.ai/cli \| sh` |
| Config | `~/.factory/settings.json` |
| Config format | JSON `customModels[]` array |
| API protocol | `provider: "generic-chat-completion-api"` (OpenAI-compatible) |
| Headless | `droid` CLI; browser sign-in may be required on first launch (risk) |
| Docs | docs.factory.ai, Z.ai devpack guide |

Setup hook writes:
```json
{"customModels":[{"displayName":"benchmark","model":"<MODEL_NAME>","baseUrl":"<PROXY_URL>","apiKey":"<KEY>","provider":"generic-chat-completion-api","maxOutputTokens":131072}]}
```

Model selection: `/model` command interactively, or CLI flag if supported. Auth risk: droid may require Factory account sign-in even for BYOK custom models — if so, remove from benchmark.

### Crush

| Property | Value |
|----------|-------|
| Install | `npm install -g @charmland/crush` |
| Config | `~/.config/crush/crush.json` |
| Config format | JSON `providers{}` object |
| API protocol | OpenAI-compatible (`base_url` + `api_key`) |
| Headless | CLI exists; non-interactive mode to verify (risk) |
| Docs | docs.z.ai/devpack/tool/crush |

Setup hook writes:
```json
{"providers":{"benchmark":{"id":"benchmark","name":"Benchmark","base_url":"<PROXY_URL>","api_key":"<KEY>"}}}
```

Model selection: `ctrl+p` interactively; CLI flag or env var if available. Non-interactive invocation to verify during testing — if no headless mode exists, remove from benchmark.

### Goose

| Property | Value |
|----------|-------|
| Install | `curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh \| bash` |
| Config | `~/.config/goose/custom_providers/benchmark.json` |
| Config format | JSON (name, engine, api_key_env, base_url, models) |
| API protocol | `engine: "openai"` (OpenAI-compatible) |
| API key | Env var via `api_key_env` (not embedded in config) |
| Headless | `goose run -t "prompt"` (documented) |
| Docs | goose-docs.ai |

Setup hook writes:
```json
{"name":"benchmark","engine":"openai","api_key_env":"LLM_API_KEY","base_url":"<PROXY_URL>","models":[{"name":"<MODEL_NAME>","context_limit":128000}],"supports_streaming":true,"requires_auth":true}
```

Invocation: `goose run -t "$PROMPT" --provider benchmark --model <MODEL_NAME>`. Output format unknown — proxy captures tokens regardless.

### DeepSeek Harness (dsh)

| Property | Value |
|----------|-------|
| Install | `npm install -g @deepseek-ai/dsh` (verify npm availability; repo uses pnpm) |
| Config | `$DSH_HOME/settings.yaml` (default `~/.dsh/settings.yaml`) |
| Config format | YAML `llm-pi-ai.providers.<id>` |
| API protocol | `api: openai-completions` |
| API key | Env var via `apiKeyEnv` (not embedded in config) |
| Headless | `dsh --profile headless "job"` — native, prints final answer, exits |
| Docs | deepseek-harness.github.io |

Setup hook writes:
```yaml
llm-pi-ai:
  providers:
    benchmark:
      apiKeyEnv: LLM_API_KEY
      api: openai-completions
      baseURL: "<PROXY_URL>"
      models:
        - id: "<MODEL_NAME>"
```

Invocation: `cd "$WORKDIR" && dsh --profile headless "$PROMPT"`. Headless profile auto-initializes on first use.

## Metric Parsers

All four use best-effort parsers with the shared `_iter_events` + `_accumulate_usage` helpers. Token/cost data comes from the logging proxy (authoritative source). Event type names are guesses until real fixtures are captured.

## Dockerfile

```dockerfile
# npm installs (Crush, DeepSeek)
RUN npm install -g @charmland/crush @deepseek-ai/dsh

# curl installs (Droid, Goose) — SHA256 pinned
RUN curl -fsSL -o /tmp/droid-install.sh https://app.factory.ai/cli && \
    echo "<hash>  /tmp/droid-install.sh" | sha256sum -c - && \
    sh /tmp/droid-install.sh && rm /tmp/droid-install.sh
RUN curl -fsSL -o /tmp/goose-install.sh \
    https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh && \
    echo "<hash>  /tmp/goose-install.sh" | sha256sum -c - && \
    bash /tmp/goose-install.sh && rm /tmp/goose-install.sh
```

Goose installs to `~/.local/bin/goose` (not /usr/local/bin) — PATH update may be required:
`ENV PATH="/root/.local/bin:${PATH}"`

## Risk Mitigation

Each harness is verified with a dummy-key container test before inclusion:
1. Write adapter
2. `docker run ... <harness> python/exercises/practice/beer-song 99 /results`
3. Success criteria: `request_count > 0` (proxy sees the request) and no auth-wall crash
4. Failing harnesses: fix adapter if possible, otherwise remove from benchmark.yaml

Known risks:
- **Droid**: Factory account browser auth may be mandatory even for BYOK
- **Crush**: No documented non-interactive mode
- **Goose**: Output format unknown (proxy mitigates)
- **dsh**: npm package availability unverified

## Design Decisions

1. **Same adapter pattern as previous 8 harnesses**: manifest.yaml + adapter.sh + setup hook + best-effort parser. No orchestrator changes.

2. **Env-var API keys preferred (Goose, dsh)**: Both support referencing env vars instead of embedding keys in config files — cleaner than Droid/Crush which require embedding.

3. **Remove-on-failure strategy**: Harnesses that cannot pass the dummy-key container test are removed from benchmark.yaml rather than shipping broken adapters. The adapter directories remain for future retry.

4. **Batch verification**: All 4 adapters created, then verified one-by-one with container tests. Failing ones documented in the commit message.
