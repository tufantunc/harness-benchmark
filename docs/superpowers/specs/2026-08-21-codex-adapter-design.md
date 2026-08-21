# Codex CLI Harness Adapter — Design Spec

**Date:** 2026-08-21
**Status:** Approved
**Parent Spec:** `2026-07-08-harness-benchmark-design.md`

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

entrypoint.sh, store.py, report.py, runner.py, dashboard — all
harness-count-agnostic.

## Harness Details

| Property | Value |
|----------|-------|
| Install | `npm install -g @openai/codex` (official npm package) |
| Config | `~/.codex/config.toml` |
| Config format | TOML `[model_providers.<id>]` table |
| API protocol | OpenAI-compatible Chat Completions (`wire_api = "chat"`) |
| API key | Env var via `env_key` (not embedded in config) |
| Headless | `codex exec` — documented non-interactive mode for CI |
| Docs | learn.chatgpt.com/docs/codex/cli |

### Why `wire_api = "chat"`

The benchmark upstream (open.bigmodel.cn `/api/paas/v4/`) speaks OpenAI Chat
Completions only — no Responses API endpoint. Codex defaults to
`wire_api = "responses"`; the custom provider must override it to `"chat"`.
The logging proxy concatenates `UPSTREAM_URL + request path`, so Codex's
`<base_url>/chat/completions` request reaches `<upstream>/chat/completions`
unchanged — same routing the other 11 adapters rely on.

### Setup hook writes

```toml
model = "<MODEL_NAME>"
model_provider = "benchmark"

[model_providers.benchmark]
name = "Benchmark Proxy"
base_url = "<MODEL_URL>"        # http://127.0.0.1:8080 inside the container
env_key = "API_KEY"             # exported by entrypoint.sh
wire_api = "chat"
```

`API_KEY` is preferred over `LLM_API_KEY` because entrypoint.sh exports it
unconditionally; env-var keys match the Goose/dsh precedent (design decision 2
of the four-harness spec).

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
Codex wraps events in a `msg` object (`{"id":…,"msg":{"type":…}}`) that the
factory's top-level `type` lookup cannot see. The parser normalizes both the
nested and flat shapes:

- `item.completed` with `item.type` in `command_execution | file_change |
  mcp_tool_call | web_search | todo_list` → `tool_calls`
- `turn.completed` → `llm_calls` (+ usage if present: `input_tokens`,
  `output_tokens`, `cached_input_tokens`)
- Legacy flat shapes (`agent_message`, `exec_command`, …) matched best-effort

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
- **First-run notices**: codex may print telemetry/update notices to stderr —
  harmless, stderr is captured to agent-stderr.log, not events.jsonl.
- **Chat wire streaming**: codex streams chat completions via SSE; the proxy
  already extracts usage from the final SSE chunk (OpenAI branch).

## Design Decisions

1. **Same adapter pattern as the previous 11 harnesses**: manifest.yaml +
   adapter.sh + setup hook + parser. No orchestrator changes.
2. **npm install over the curl installer**: matches the existing Dockerfile
   npm block; no SHA256 pinning burden beyond what npm provides; official
   package.
3. **`env_key` over embedded key**: keeps secrets out of config files
   (Goose/dsh precedent).
4. **Bespoke parser over the factory**: Codex's nested `msg` envelope needs
   one level of unwrapping the shared factory does not do.
5. **Remove-on-failure strategy**: unchanged from the four-harness spec.
