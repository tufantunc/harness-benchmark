# Codex CLI Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenAI Codex CLI as harness 12 following the established adapter pattern (spec: `docs/superpowers/specs/2026-08-21-codex-adapter-design.md`).

**Architecture:** Standard adapter directory contract — `harnesses/codex/{manifest.yaml,adapter.sh}`. Setup hook writes `~/.codex/config.toml` custom provider pointing at the logging proxy (`wire_api = "chat"`). `codex exec --json` streams JSONL to `/output/events.jsonl`; a bespoke parser (nested `msg` envelope) extracts `tool_calls`/`llm_calls`.

**Tech Stack:** bash, TOML config, Python (pytest), Docker, npm `@openai/codex`.

## Global Constraints

- Upstream is OpenAI Chat Completions only → `wire_api = "chat"` (never `"responses"`).
- `env_key = "API_KEY"` (exported by `docker/entrypoint.sh:65`), not `LLM_API_KEY`.
- Token/cost metrics come from the proxy; parser only produces `tool_calls`/`llm_calls` (+ usage if events carry it).
- Exit code 124 = timeout (handled by entrypoint, adapter must not swallow it).
- No orchestrator changes (entrypoint.sh, runner.py, store.py untouched).

---

### Task 1: Codex event parser (TDD)

**Files:**
- Test: `tests/test_extract_metrics.py` (append)
- Fixture: `tests/fixtures/codex-events.jsonl` (create)
- Modify: `container/extract_metrics.py`

**Interfaces:**
- Consumes: `Metrics`, `_iter_events`, `_accumulate_usage` from `container/extract_metrics.py`
- Produces: `parse_codex_events(lines: list[str]) -> Metrics`; registered as `"codex"` in `PARSERS`

- [ ] **Step 1: Write the failing test + fixture**

`tests/fixtures/codex-events.jsonl` (nested `msg` envelope — current codex exec --json shape; one turn with two tool items and usage):

```jsonl
{"id":"1","msg":{"type":"thread.started","thread_id":"t1"}}
{"id":"2","msg":{"type":"turn.started"}}
{"id":"3","msg":{"type":"item.completed","item":{"id":"i1","type":"command_execution","command":"ls","exit_code":0,"aggregated_output":"..."}}}
{"id":"4","msg":{"type":"item.completed","item":{"id":"i2","type":"file_change","changes":[{"path":"bob.py","kind":"add"}]}}}
{"id":"5","msg":{"type":"item.completed","item":{"id":"i3","type":"agent_message","content":"done"}}}
{"id":"6","msg":{"type":"turn.completed","usage":{"input_tokens":1200,"output_tokens":300,"cached_input_tokens":450}}}
```

Append to `tests/test_extract_metrics.py`:

```python
def test_extract_codex_events(fixtures_dir):
    events_file = fixtures_dir / "codex-events.jsonl"
    metrics = extract_metrics(events_file, format="codex")

    assert metrics.llm_calls == 1  # one turn.completed
    assert metrics.tool_calls == 2  # command_execution + file_change
    assert metrics.tokens_input == 1200
    assert metrics.tokens_output == 300
    assert metrics.tokens_cached == 450


def test_codex_flat_legacy_shape(tmp_path):
    """Older codex builds emit flat {"type": ...} events — tolerate both."""
    events_file = tmp_path / "flat.jsonl"
    events_file.write_text(
        '{"type":"agent_message","message":"hi"}\n'
        '{"type":"exec_command","command":"ls"}\n'
    )
    metrics = extract_metrics(events_file, format="codex")

    assert metrics.llm_calls == 1
    assert metrics.tool_calls == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_extract_metrics.py -k codex -v`
Expected: FAIL with "Unknown format: codex"

- [ ] **Step 3: Implement `parse_codex_events`**

In `container/extract_metrics.py`, add after `parse_cline_events`:

```python
def parse_codex_events(lines: list[str]) -> Metrics:
    """Parse codex exec --json output.

    Events are wrapped in a msg envelope: {"id":…,"msg":{"type":…}}.
    item.completed with item.type command_execution/file_change/mcp_tool_call/
    web_search/todo_list = tool call; turn.completed = one LLM turn (+ usage).
    Older builds emit flat {"type": …} events — both shapes are handled.
    Token/cost data is captured by the logging proxy (authoritative source).
    """
    m = Metrics()
    tool_item_types = (
        "command_execution", "file_change", "mcp_tool_call",
        "web_search", "todo_list",
    )
    for evt in _iter_events(lines):
        msg = evt.get("msg", evt)  # unwrap envelope; flat events pass through
        msg_type = msg.get("type", "")
        if msg_type == "item.completed":
            item = msg.get("item", {})
            if item.get("type") in tool_item_types:
                m.tool_calls += 1
        elif msg_type == "turn.completed":
            m.llm_calls += 1
            usage = msg.get("usage") or {}
            if usage:
                _accumulate_usage(m, {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_read_tokens": usage.get("cached_input_tokens", 0),
                })
        elif msg_type in ("agent_message", "response"):
            m.llm_calls += 1
        elif msg_type in ("exec_command", "patch_apply", "mcp_tool_call"):
            m.tool_calls += 1
    return m
```

Register in `PARSERS` (before the best-effort expansion line):

```python
PARSERS = {
    ...
    "cline": parse_cline_events,
    "codex": parse_codex_events,
    ...
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `.venv/bin/pytest tests/test_extract_metrics.py -v`
Expected: all PASS (including pre-existing)

- [ ] **Step 5: Commit**

```bash
git add container/extract_metrics.py tests/test_extract_metrics.py tests/fixtures/codex-events.jsonl
git commit -m "feat: codex event parser (nested msg envelope + flat legacy shapes)"
```

---

### Task 2: Adapter directory

**Files:**
- Create: `harnesses/codex/manifest.yaml`
- Create: `harnesses/codex/adapter.sh` (executable, mode 100755)

**Interfaces:**
- Consumes: entrypoint.sh calls `adapter.sh <prompt-file> <workdir> <model-flag>`; env `MODEL_URL`, `API_KEY`, `MODEL_NAME` available to the setup hook
- Produces: `/output/events.jsonl` (JSONL), `/output/agent-exit-code`; metric_format `codex`

- [ ] **Step 1: Write manifest.yaml**

```yaml
# harnesses/codex/manifest.yaml
name: codex
version: "latest"
install: npm install -g @openai/codex

invoke:
  command: codex exec --json --skip-git-repo-check --sandbox danger-full-access - < "$PROMPT_FILE"
  model_flag: -m $MODEL_NAME

setup: |
  mkdir -p ~/.codex
  cat > ~/.codex/config.toml <<CODEXEOF
  model = "$MODEL_NAME"
  model_provider = "benchmark"

  [model_providers.benchmark]
  name = "Benchmark Proxy"
  base_url = "$MODEL_URL"
  env_key = "API_KEY"
  wire_api = "chat"
  CODEXEOF

metric_source: events.jsonl
metric_format: codex
```

- [ ] **Step 2: Write adapter.sh**

```bash
#!/usr/bin/env bash
# harnesses/codex/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"

cd "$WORKDIR"
codex exec \
    $MODEL_FLAG \
    --json \
    --skip-git-repo-check \
    --sandbox danger-full-access \
    - < "$PROMPT_FILE" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
```

- [ ] **Step 3: Make executable + sanity-check**

Run: `chmod +x harnesses/codex/adapter.sh && bash -n harnesses/codex/adapter.sh && git ls-files -s harnesses/crush/adapter.sh`
Expected: no syntax errors; crush mode shows `100755` (codex must match after `git add`)

- [ ] **Step 4: Commit**

```bash
git add harnesses/codex/
git commit -m "feat: add codex adapter (manifest + headless exec invocation)"
```

---

### Task 3: Dockerfile install + benchmark registration

**Files:**
- Modify: `docker/Dockerfile:22-28` (npm block)
- Modify: `benchmark.yaml:22` (harnesses list)

- [ ] **Step 1: Add npm install**

Append to the existing global npm `RUN` block:

```dockerfile
RUN npm install -g opencode-ai && \
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent && \
    npm install -g @jetbrains/junie && \
    npm install -g cline && \
    npm install -g @kilocode/cli && \
    npm install -g @charmland/crush && \
    npm install -g @deepseek-ai/dsh && \
    npm install -g @openai/codex
```

- [ ] **Step 2: Register in benchmark.yaml**

```yaml
harnesses: [opencode, pi, grok, junie, cline, kilo, kimi, autohand, crush, goose, dsh, codex]
```

- [ ] **Step 3: Verify npm package exists with expected binary**

Run: `npm view @openai/codex name version dist.tarball`
Expected: `@openai/codex` + a version + tarball URL (fail loudly before docker build)

- [ ] **Step 4: Commit**

```bash
git add docker/Dockerfile benchmark.yaml
git commit -m "feat: install codex CLI and register in benchmark"
```

---

### Task 4: Dummy-key container verification

**Files:** none (verification only; artifacts under `results/`, gitignored)

- [ ] **Step 1: Build image**

Run: `docker build -t harness:latest -f docker/Dockerfile .`
Expected: build succeeds, codex binary installed

- [ ] **Step 2: Dummy-key container test**

Run: `docker run --rm -e MODEL_URL=https://open.bigmodel.cn/api/paas/v4/ -e PROTOCOL=openai -e MODEL_NAME=glm-5.2 -e LLM_API_KEY=dummy-key -e TASK_TIMEOUT=120 -v "$(pwd)/results:/results" harness:latest codex python/exercises/practice/beer-song 99 /results`
Expected: one JSON metrics line on stdout

- [ ] **Step 3: Check success criteria**

Run: `cat results/artifacts/codex/python/beer-song/rep-99/proxy-analysis.json`
Expected: `request_count > 0` (proxy saw the request; auth passed through to upstream which rejects dummy key — that's fine, the point is no local auth wall). If codex crashes before any request (auth/config error), fix adapter; if unfixable, remove `codex` from benchmark.yaml per spec decision 5.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: codex adapter verification findings"
```
