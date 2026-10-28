# opencode2, prime-agent, whycodes adapters — design

Date: 2026-10-28. Harnesses 17–19, standard adapter contract
(`harnesses/<name>/{manifest.yaml,adapter.sh}`), all pointed at the logging
proxy through an OpenAI-compatible Chat Completions provider.

Candidates evaluated alongside and rejected: Factory droid (public build
still needs a paid Factory account even for BYOK), OpenBot (Electron app
wrapping opencode/claude/cline, no one-shot CLI, account login). Hermes Agent
and OpenClaw are viable but deferred (local gateway lifecycle; Node ≥ 24).

## opencode2 — OpenCode v2 (`@opencode/cli` 2.2.0)

v2 is a new npm package maintained in parallel with v1 (`opencode-ai`, still
`latest`), so it is a separate harness rather than an upgrade of `opencode`.

- Install: `npm install --prefix /opt/opencode2` + `/usr/local/bin/opencode2`
  symlink — both packages ship an `opencode` bin.
- Config: v1's `$WORKDIR/opencode.json` provider block loads unchanged
  (`opencode debug config` shows it translated to
  `aisdk:@ai-sdk/openai-compatible`).
- Invocation differences from v1, all found empirically:
  - `run --dir` is gone → `cd "$WORKDIR"`.
  - Default is a shared background service → `--standalone` (private
    `serve --stdio` child that exits with the run; no leftover process).
  - `run` hangs before its first request while stdin is open → `< /dev/null`.
- Events: v1 shapes (`step_start`/`tool_use`/`step_finish`/`text`), but no
  `step_finish` for the final text-only step → parser `opencode2` reuses the
  v1 parser and zeroes `llm_calls` so the proxy request count wins.
- Each session makes one extra title-generation request (visible in proxy).

## prime-agent — Prime Agent 0.10.1

- Install: pinned `linux-arm64` release archive (SHA256 from the release's
  `manifest.json`), installed with the archive's own `install.sh --archive`
  (launcher in `~/.local/bin`, Python kernel pre-warmed via uv at build time).
- Config: `~/.prime/agent/models.json` custom provider
  (`api: openai-completions`, `baseUrl`, `apiKey`); `settings.json` turns
  telemetry off (same file `prime-agent telemetry off` writes) plus
  `DO_NOT_TRACK=1`.
- Invocation: `prime-agent --mode json --cwd W --provider benchmark
  --model M -p PROMPT`. Print mode runs in-process (no daemon); no permission
  system, so no approval flag is needed.
- No `--offline`: the Python skills (`edit`, `goal`, `refine`, …) are
  uv-installed into the kernel venv at session start (~1.5s, needs network);
  `--offline` cancels that and the skills are unavailable. A build-time
  pre-warm run against an unreachable provider did not install them.
- Design note: the model gets a single `python_repl` tool; every other
  capability is called from Python. Scores reflect that design.
- Events: pi-shaped JSONL. Parser `prime-agent` reads usage from assistant
  `message_end` only and tools from `tool_execution_start` only (pi's parser
  would count each call up to three times here). `usage.input` excludes cache
  reads; the proxy stays authoritative.
- The adapter drops `message_update` lines: each carries a snapshot of the
  whole message so far, so the file grows quadratically (one real task: 51 MB,
  99.7% of it these lines; a filtered 11-request run: 368 KB). `grep --line-buffered` so a
  timeout kill keeps everything written so far.
- `python_repl` has no per-call timeout: a model-written exponential
  "speed check" ran until the task timeout (tests still passed). Exits 0 even
  when the provider fails (e.g. 429).

## whycodes — WhyCodes 0.6.24

- Install: upstream has no linux-arm64 binary → multi-stage build
  (`rust:1.97-bookworm`, tag `v0.6.24` checked against its commit SHA,
  upstream's `cargo build --release --locked -p whycodes-cli --features
  bundled-sqlite`). `rust-toolchain.toml` is removed so rustup does not fetch
  the current stable over the pinned image toolchain.
- Config: `~/.whycodes/config.toml` — `[providers.benchmark]` with `name`
  (required in 0.6.24 despite the docs), `base_url`, `api_key` (env keys are
  ignored for custom providers), and `[default_model]`. `-P` only accepts
  built-in provider names, so no model flag.
- Invocation: `whycodes generate PROMPT -d W --format stream-json
  --approve-tools` (headless denies permission `ask` otherwise),
  `WHYCODES_SANDBOX=off` (no bubblewrap in the container).
- Events: NDJSON; one `usage` event per LLM request, `tool_start` per tool
  call; the final `result.usage` is the run total and is not re-added.
- `usage` events carry no cache figures, so `tokens_cached` comes from the
  proxy, which now reads OpenAI Chat `prompt_tokens_details.cached_tokens`
  (before that it was 0 for whycodes and 11 other OpenAI-protocol harnesses;
  `scripts/backfill-openai-cache.py` recomputes stored runs).
- Retries 429s itself (4 tries, ~20s) before failing.

## Verification

- Parser unit tests with fixtures captured from local runs against a mock
  OpenAI-compatible upstream (paths sanitized to `/workdir`).
- Container smoke test against the mock upstream (plumbing: config, proxy
  capture, events, exit), then a real-key run per harness.
- Real runs (glm-5.3, python/book-store), all 20 tests passing:
  opencode2 210s / 9 requests (8 steps + title; 7 `step_finish` for 8
  `step_start`, confirming the parser choice); prime-agent 141s / 7 requests,
  parsed calls and tokens equal to the proxy's; whycodes 191s / 8 requests.
