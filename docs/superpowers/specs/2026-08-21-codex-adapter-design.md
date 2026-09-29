# Codex CLI Harness Adapter — Design Spec

**Date:** 2026-08-21
**Status:** PARKED 2026-09-29 — removed from benchmark.yaml
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

> **Parking note (2026-09-29):** This spec's verification was a false
> positive — the dummy-key probe could not detect that no upstream actually
> serves `/responses` (BigModel and Z.ai both return 404 with a real key;
> auth is checked before routing, so dummy-key probes return 401 for any
> path). Codex removed `wire_api = "chat"` in Feb 2026 (still rejected in
> 0.159.0), leaving no viable wire protocol on our platforms. The adapter,
> parser, and proxy Responses branches remain in the tree for a future
> revival via a proxy Responses→Chat bridge or a Responses-capable upstream.

## Overview

Add OpenAI Codex CLI as harness 12, extending the benchmark to a twelve-harness
comparison with the same LLM (GLM 5.2 via proxy). Codex is the reference
implementation of the "agent harness" category and is frequently requested as a
baseline.

## Scope

- Create `harnesses/codex/` adapter (manifest.yaml + adapter.sh)
- Add a bespoke `parse_codex_events` parser to `container/extract_metrics.py`
- Update `docker/Dockerfile` with the install command
- Update `benchmark.yaml` harness list
- Verify with the dummy-key container test; remove from benchmark.yaml if it
  cannot connect through the proxy

## No Changes Needed

store.py, report.py, runner.py, dashboard — all harness-count-agnostic.

Two additive proxy extensions were required (see Design Decisions 6): the
Responses API SSE usage branch in `proxy.js` and the `instructions` system
prompt branch in `analyze-proxy.js`. Both are additive `if` branches that
leave all existing harness paths byte-identical.

## Harness Details

| Property | Value |
|----------|-------|
| Install | `npm install -g @openai/codex` (official npm package) |
| Config | `~/.codex/config.toml` |
| Config format | TOML `[model_providers.<id>]` table |
| API protocol | OpenAI Responses API (`wire_api = "responses"`) |
| API key | Env var via `env_key` (not embedded in config) |
| Headless | `codex exec` — documented non-interactive mode for CI |
| Docs | learn.chatgpt.com/docs/codex/cli |

### Why `wire_api = "responses"`

Codex ≥0.149 removed Chat Completions support entirely (`wire_api = "chat"`
is a hard config error) — the Responses API is the only wire protocol. The
benchmark upstream (open.bigmodel.cn `/api/paas/v4/`) serves a
`/responses` endpoint (verified: 401 with dummy credentials, i.e. the route
exists), so codex talks Responses straight through the transparent proxy.
Two small additive proxy extensions were needed (see Design Decisions).

The logging proxy concatenates `UPSTREAM_URL + request path`, so codex's
`<base_url>/responses` request reaches `<upstream>/responses` unchanged —
same routing the other 11 adapters rely on.

### Setup hook writes

```toml
model = "<MODEL_NAME>"
model_provider = "benchmark"
model_context_window = 1048576
model_max_output_tokens = 131072

[model_providers.benchmark]
name = "Benchmark Proxy"
base_url = "<MODEL_URL>"        # http://127.0.0.1:8080 inside the container
env_key = "API_KEY"             # exported by entrypoint.sh
wire_api = "responses"
```

`API_KEY` is preferred over `LLM_API_KEY` because entrypoint.sh exports it
unconditionally; env-var keys match the Goose/dsh precedent (design decision 2
of the four-harness spec). The context/output limits are GLM-5.2's documented
values (1M context, 128K output) — without them codex warns about missing
model metadata and falls back to conservative defaults.

### Invocation

```bash
codex exec \
    -m "$MODEL_NAME" \
    --json \
    --skip-git-repo-check \
    --sandbox danger-full-access \
    - < "$PROMPT_FILE"
```

- Prompt via stdin (`-`) to avoid argv length limits.
- `--json` emits JSONL events on stdout; the adapter redirects them to
  `/output/events.jsonl`.
- `--sandbox danger-full-access`: container isolation replaces Codex's own
  sandbox (parity with the yolo/bypass modes of the other adapters); Codex's
  Linux sandbox (landlock/seccomp) is also unreliable as root in Docker.
- `--skip-git-repo-check`: workdir is normally a git repo already (entrypoint
  inits one), but the flag guards against `git init` failure.
- `codex exec` never prompts for approvals (approval policy `never` is the
  exec default), so no auth wall exists as long as `env_key` resolves.

## Metric Parser

Bespoke `parse_codex_events` (not the `_BEST_EFFORT_FORMATS` factory) because
codex emits structured `item.completed` events whose tool/LLM signal lives in
a nested `item.type` field the factory cannot see. Verified against a live
container run — events are flat (`{"type":"item.completed","item":{…}}`);
builds wrapping events in a `msg` envelope are tolerated.

- `item.completed` with `item.type` in `command_execution | file_change |
  mcp_tool_call | web_search | todo_list` → `tool_calls`
- `turn.completed` → `llm_calls` (+ usage if present: `input_tokens`,
  `output_tokens`, `cached_input_tokens`)
- `error` / `turn.failed` count as nothing (retried requests surface as proxy
  `request_count` instead)
- Flat legacy types (`agent_message`, `exec_command`, …) matched best-effort

Token/cost data remains captured by the logging proxy (authoritative source);
the parser provides `tool_calls`/`llm_calls` counts only.

## Dockerfile

Appended to the existing global npm block:

```dockerfile
RUN npm install -g @openai/codex
```

Unpinned like the other npm harnesses (crush, dsh, junie). The npm package
ships a native binary; no extra PATH setup needed (`npm bin -g` is on PATH).

## Risk Mitigation

Dummy-key container test before inclusion (same as the four-harness spec):

1. Write adapter
2. `docker run … codex python/exercises/practice/beer-song 99 /results`
3. Success criteria: `request_count > 0` in proxy analysis and no auth crash
4. On failure: fix adapter if possible, otherwise remove from benchmark.yaml

Known risks:

- **Event schema drift**: `codex exec --json` output is still marked
  experimental; the parser tolerates both nested and flat shapes and defaults
  to zero rather than crashing (proxy remains authoritative for tokens).
- **Unknown-model metadata warning**: codex prints "Model metadata for
  glm-5.2 not found. Defaulting to fallback metadata" even with
  `model_context_window`/`model_max_output_tokens` set — a known upstream
  issue (openai/codex#19185) where config values may be clamped by fallback
  metadata. Non-fatal; the keys remain the best available lever.
- **Responses SSE usage**: usage arrives in the `response.completed` event
  under `response.usage`; the proxy extension extracts it (plus
  `input_tokens_details.cached_tokens` for cache reads).

## Design Decisions

1. **Same adapter pattern as the previous 11 harnesses**: manifest.yaml +
   adapter.sh + setup hook + parser. No orchestrator changes.
2. **npm install over the curl installer**: matches the existing Dockerfile
   npm block; no SHA256 pinning burden beyond what npm provides; official
   package.
3. **`env_key` over embedded key**: keeps secrets out of config files
   (Goose/dsh precedent).
4. **Bespoke parser over the factory**: codex's `item.completed` payload needs
   one level of unwrapping the shared factory does not do.
5. **Remove-on-failure strategy**: unchanged from the four-harness spec.
6. **Responses API instead of Chat Completions (revision during
   implementation)**: the original design assumed `wire_api = "chat"` because
   the upstream was believed chat-only; probing showed BigModel serves
   `/responses`, and codex ≥0.149 rejects `wire_api = "chat"` outright. The
   proxy gained an additive `response.completed` usage branch (Responses SSE
   carries usage under `response.usage`, not top-level) and
   `analyze-proxy.js` gained an `instructions` system-prompt branch — without
   these, token and system-prompt metrics would silently read 0 for codex.
7. **Pinned model metadata**: `model_context_window = 1048576` /
   `model_max_output_tokens = 131072` (GLM-5.2 documented values) prevent
   codex from degrading to fallback metadata for an unknown model id.
