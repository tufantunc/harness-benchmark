# harness-benchmark — Design Spec

**Date:** 2026-07-08
**Status:** Approved
**Repo:** https://github.com/tufantunc/harness-benchmark
**Pages:** https://tufantunc.github.io/harness-benchmark/

## 1. Overview

### Purpose

Benchmark coding agent harnesses (opencode, pi, and future additions) against each other using an **identical LLM**, **identical tasks**, and **identical isolation**. The only variable is the harness — its system prompt, tool orchestration, and context management.

### Scope (MVP)

| Dimension | Decision |
|-----------|----------|
| Harnesses | opencode, pi |
| Model | GLM 5.2 (default, swappable via URL) |
| Tasks | Aider Polyglot Benchmark — Python (34) + JavaScript (49) = 83 exercises |
| Framework | inspect-ai on host |
| Isolation | Docker container per (harness x task x repetition) |
| Repetitions | 3 (configurable) |
| Results | SQLite store + GitHub Pages leaderboard |

### Non-Goals (MVP)

- Sub-agents, plan mode, or other harness-specific extensions
- Multimodal tasks
- Non-Exercism task sources
- Real-time leaderboard (static generation only)
- CI/automated runs (manual `./benchmark.sh` only for now)

## 2. Architecture

**Approach: Single base image + host-side inspect-ai orchestrator.**

inspect-ai runs on the host. For each (harness x exercise x repetition) combination, it spawns a fresh, stateless Docker container that runs one agent on one task, collects metrics, and emits them via stdout + mounted volume.

```
HOST (inspect-ai)
  task_loader.py    -> 83 exercises to inspect-ai samples
  solver.py         -> docker run per task (stateless container)
  scorer.py         -> test run + metric normalization
  store.py          -> SQLite CRUD (idempotent UPSERT)
  report.py         -> leaderboard generation (html/md/json)
        |
        | docker run --rm per (harness x task x rep)
        v
CONTAINER (harness:latest) — single image, stateless
  entrypoint.sh <harness> <exercise-path> <rep>
    1. Copy exercise stub to workdir (pristine)
    2. Setup hook -> harness-specific provider config (from URL+protocol)
    3. Adapter invokes agent -> events.jsonl
    4. Run test suite -> test-output.txt
    5. Collect: diff, metrics.json
    6. Emit metrics.json to stdout, artifacts to mounted volume
```

**Key properties:**
- Container is **stateless** — no state persists between runs.
- Results written to a **mounted volume** (`./results`), not parsed from stdout.
- Model API key passed as **environment variable** to the container.
- Single Docker image contains both harnesses + all language tooling.

### Why single image (Approach A)

Chosen over per-language images (Approach B) and multi-stage builds (Approach C):

- **Maximal reproducibility** — one `docker build` produces identical environment for all developers.
- **Lowest friction** for contributors — clone, build once, run.
- Both harnesses are Node-based and share the same Node runtime.
- Image size (~2-3 GB) is acceptable for a build-once, cache-locally workflow.
- New harness = one `adapter.sh` + one Dockerfile line, not a new image.

## 3. Harness Registry

New harnesses are added by dropping a folder under `harnesses/`. No orchestrator code changes needed.

```
harnesses/
  opencode/
    manifest.yaml    # metadata + invocation contract + setup hook
    adapter.sh       # invocation logic
  pi/
    manifest.yaml
    adapter.sh
  _template/         # scaffolding for new harnesses
    manifest.yaml
    adapter.sh
```

### manifest.yaml format

```yaml
name: opencode
version: 0.1.48
install: npm install -g opencode-ai
invoke:
  command: opencode run "$PROMPT" --format json --dir "$WORKDIR" --auto
  model_flag: --model benchmark/$MODEL_NAME
setup: |
  # Generates harness-specific provider config from URL+protocol
  # Variables available: $MODEL_URL, $PROTOCOL, $MODEL_NAME, $API_KEY
  ...
metric_source: events.jsonl
metric_format: opencode-events    # selects the parser in extract-metrics.py
```

inspect-ai discovers all `harnesses/*/manifest.yaml` files and includes those listed in `benchmark.yaml` (`harnesses: [opencode, pi]`).

## 4. Results Store

Incremental leaderboard support. Results are keyed by content identity, not run timestamp.

### SQLite schema

```sql
CREATE TABLE runs (
  id            INTEGER PRIMARY KEY,
  run_id        TEXT,           -- batch grouping (UUID per benchmark.sh invocation)
  harness       TEXT,           -- 'opencode' | 'pi' | 'cursor' | ...
  model         TEXT,           -- 'glm-5.2' | 'claude-sonnet-4-5' | ...
  language      TEXT,           -- 'python' | 'javascript'
  exercise      TEXT,           -- 'affine-cipher'
  repetition    INTEGER,        -- 1, 2, 3
  success       BOOLEAN,
  partial_score REAL,
  tokens_input  INTEGER,
  tokens_output INTEGER,
  tokens_cached INTEGER,
  cost_usd      REAL,
  duration_sec  REAL,
  tool_calls    INTEGER,
  llm_calls     INTEGER,
  diff_loc      INTEGER,
  timed_out     BOOLEAN,
  tampered      BOOLEAN,
  artifact_path TEXT,           -- relative path to artifacts/<run-id>/...
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(harness, model, language, exercise, repetition)
);
```

### Idempotency

The `UNIQUE(harness, model, language, exercise, repetition)` constraint enables UPSERT semantics. Re-running the same combination overwrites the previous result. This supports:

- **Incremental runs:** Add a new harness, run only it, merge into existing leaderboard.
- **Retry failed:** Re-run only combinations where `success = false`.
- **Skip existing:** `--skip-existing` flag skips combinations already in the store.

### Filesystem artifacts (not committed)

Raw artifacts per run are stored under `results/artifacts/<run-id>/<harness>/<language>/<exercise>/rep-<N>/`:
- `events.jsonl` — agent transcript
- `diff.patch` — code changes
- `test-output.txt` — test stdout/stderr
- `metrics.json` — normalized metrics

These are `.gitignore`d (large, machine-specific). The SQLite store is committed for incremental leaderboard continuity.

### Portability

```bash
./scripts/report.sh --export results.json   # full store dump (portable)
./scripts/report.sh --import results.json   # load on another machine
```

## 5. Task Lifecycle (Container-Internal)

For each (harness x exercise x repetition), the container executes:

```
entrypoint.sh <harness> <exercise-path> <rep>
  |
  |-- 1. SETUP
  |     Copy exercise from polyglot-benchmark/ (read-only, baked into image)
  |       to /workdir/ (pristine stub only; test files excluded)
  |
  |-- 2. SETUP HOOK (from manifest.yaml)
  |     Generate harness-specific provider config from URL+protocol
  |     (e.g., pi's models.json, opencode's opencode.json)
  |
  |-- 3. PROMPT ASSEMBLE
  |     prompt = cat .docs/instructions.md
  |            + addendum (fixed text from benchmark.yaml)
  |     -> /workdir/prompt.txt
  |
  |-- 4. AGENT INVOKE
  |     timeout $TASK_TIMEOUT \
  |       <adapter.sh> /workdir/prompt.txt /workdir $MODEL_NAME
  |       > /output/events.jsonl 2>/output/agent-stderr.log
  |
  |-- 5. TEST RUN (after agent finishes)
  |     Copy test files into /workdir/ (agent never sees them during work)
  |     python: pytest <test_file> --tb=short
  |     js:     npm run test  (with xtest->test sed transform)
  |     -> /output/test-output.txt
  |
  |-- 6. COLLECT
  |     git diff --no-color -> /output/diff.patch
  |     extract-metrics.py events.jsonl -> metrics (per-harness parser)
  |     check-tamper.sh -> did agent modify test files?
  |     -> /output/metrics.json
  |
  |-- 7. EMIT
  |     cat /output/metrics.json -> stdout (inspect-ai captures)
  |     cp -r /output/ -> mounted results/artifacts/ volume
```

### Rules

- Agent sees **only** the stub file and `.docs/` instructions — never the test file.
- Test files are copied into the workdir **after** the agent finishes (Aider's method).
- JS exercises get the `xtest(` -> `test(` sed transform (Aider's npm-test.sh method) to enable all Exercism skipped cases.
- On timeout: `success = false`, partial metrics still collected.
- `entrypoint.sh` always emits `metrics.json` to stdout — inspect-ai parses it.

## 6. Harness Adapter & Metric Extraction

### Adapter contract

Each `adapter.sh` has one job: invoke the agent and write `events.jsonl`. It receives `$1=prompt-file`, `$2=workdir`, `$3=model-name`.

### Metric extraction

Both harnesses emit JSON event streams, but in different formats. A single `extract-metrics.py` script in the container dispatches to per-format parsers based on the harness's `metric_format` manifest field.

**pi format** (`--mode json`): Each line is a JSON event. `AssistantMessage` events contain a `usage` object with `{input, output, cacheRead, cacheWrite, cost: {input, output, cacheRead, cacheWrite, total}}`. Parser aggregates across all assistant messages.

**opencode format** (`--format json`): Raw JSON events. Token/cost extracted from events if present; fallback to `opencode export <session-id>` for the session transcript if events lack usage data.

### Output: metrics.json (unified schema)

Regardless of harness, `metrics.json` follows one schema:

```json
{
  "harness": "pi",
  "model": "glm-5.2",
  "language": "python",
  "exercise": "affine-cipher",
  "repetition": 1,
  "success": true,
  "test_exit_code": 0,
  "agent_exit_code": 0,
  "timed_out": false,
  "tokens_input": 4231,
  "tokens_output": 567,
  "tokens_cached": 8900,
  "cost_usd": 0.021,
  "tool_calls": 8,
  "llm_calls": 4,
  "duration_sec": 47.3,
  "diff_loc": 42,
  "lint_pass": true
}
```

This schema maps 1:1 to the SQLite store columns and the inspect-ai scorer.

## 7. Config System

Single `benchmark.yaml` controls everything. CLI flags override `.env`, which overrides `benchmark.yaml` defaults.

### Override hierarchy (highest to lowest priority)

```
1. CLI flag        ./benchmark.sh --model-url ... --repetitions 1
2. .env            LLM_API_KEY=...
3. benchmark.yaml  (defaults)
```

### benchmark.yaml

```yaml
model:
  url: https://open.bigmodel.cn/api/paas/v4/    # OpenAI-compatible endpoint
  protocol: openai                                # openai | anthropic | google
  name: glm-5.2                                   # model name as endpoint expects
  api_key_env: LLM_API_KEY                        # which env var holds the key

task:
  source: polyglot
  languages: [python, javascript]
  addendum: |
    Modify only the supplied files. Don't rename functions or classes.
    Only use standard libraries. Don't install packages.

run:
  repetitions: 3
  timeout_sec: 600
  skip_existing: true
  retry_failed: false
  parallel: 1

harnesses: [opencode, pi]

docker:
  image: harness:latest
  results_volume: ./results

reporting:
  output: [sqlite, html, markdown]
  pages_path: docs
  auto_commit: true
```

### Why URL-based instead of provider

A provider name (e.g., "zai") locks the endpoint. The same model (GLM 5.2) can be reached via ZAI's official endpoint, OpenRouter, or a self-hosted proxy. Specifying `url + protocol + name` is provider-agnostic and more reproducible. Each harness's setup hook translates these three values into its own native provider config format.

### .env.example

```env
# Single key, single endpoint — provider-agnostic
LLM_API_KEY=your-api-key
# benchmark.yaml defines url/protocol/name
# Override model via flags:
#   ./benchmark.sh --model-url https://api.anthropic.com \
#                  --model-protocol anthropic \
#                  --model-name claude-sonnet-4-5
HARNESS_IMAGE=harness:latest
REPETITIONS=3
TASK_TIMEOUT=600
```

## 8. Evaluation & Scoring

### Success criterion

A task succeeds if and only if:
1. The test suite exits with code 0 (`pytest` for Python, `jest` for JS).
2. The agent did not tamper with the test files (`git diff` check).

### Tamper detection

```python
def score(state, target):
    test_exit = state.output["test_exit_code"]
    test_files = target.config["test_files"]
    diff = parse_diff(state.output["diff_patch"])
    tampered = any(f in diff for f in test_files)
    return Score(
        value=1.0 if (test_exit == 0 and not tampered) else 0.0,
        metadata={"tampered": tampered, "test_exit_code": test_exit}
    )
```

### Per-task metrics

| Metric | Source |
|--------|--------|
| `success` | test exit code + tamper check |
| `tokens_input` / `tokens_output` / `tokens_cached` | events.jsonl parser |
| `cost_usd` | harness-reported (model price x tokens) |
| `tool_calls` / `llm_calls` | events.jsonl parser |
| `duration_sec` | wall-clock (container start to finish) |
| `diff_loc` | `git diff --stat` |
| `timed_out` | container exit reason |

### Aggregate metrics (per harness x model)

| Metric | Formula |
|--------|---------|
| `success_rate` | success_count / total_tasks |
| `pass@k` | at least 1 success in k repetitions |
| `pass@1` | first-attempt success rate |
| `avg_cost_per_task` | mean(cost_usd where success=true) |
| `tokens_per_success` | mean(total_tokens where success=true) |
| `avg_duration` | mean(duration_sec) |
| `avg_tool_calls` | mean(tool_calls) |

### Variance

With repetitions=3, each task produces 3 results. The report shows:
- **pass@k** (optimistic: at least 1 success in k tries)
- **pass@1** (most common metric)
- **mean +/- std** for cost and tokens (box plot for distribution)

### Tie-breaker ranking

When two harnesses have equal success_rate:
1. success_rate (higher wins)
2. tokens_per_success (lower wins)
3. avg_cost_per_task (lower wins)
4. avg_duration_sec (lower wins)

## 9. Reporting & Leaderboard

Reporter queries the SQLite store and emits three formats.

### HTML leaderboard (`docs/index.html` — GitHub Pages)

Self-contained single file, embedded CSS+JS, no external dependencies. Generated by `report.py`:

- Model selector (compare multiple models)
- Language filter (all / python / javascript)
- Summary table: rank, harness, success, pass@k, tokens/success, cost/run, avg time
- Per-language breakdown table
- Per-exercise detail table (filterable, links to artifacts)
- Box plot: tokens/success distribution

Data is embedded as `docs/assets/leaderboard-data.json`, read by the HTML's JS.

### Markdown leaderboard (`docs/leaderboard.md`)

Mirrors the HTML summary table in GitHub-flavored markdown. Linked from README.

### SQLite store (`results/store.db`)

Committed for incremental leaderboard continuity. Export/import commands for portability.

### Publish flow

```
benchmark.sh finishes:
  -> report.py --model glm-5.2
       -> docs/index.html (overwrite)
       -> docs/leaderboard.md (overwrite)
       -> docs/assets/leaderboard-data.json
       -> results/store.db (updated)
  -> if reporting.auto_commit:
       git add docs/ results/store.db
       git commit -m "benchmark: glm-5.2 results (2026-07-08)"
       git push origin main
       -> GitHub Pages auto-rebuild
```

## 10. Project Structure

```
harness-benchmark/
├── README.md
├── .env.example
├── .gitignore
├── .gitmodules                        # polyglot-benchmark submodule
├── benchmark.yaml                     # main config
│
├── docker/
│   ├── Dockerfile                     # single image (Approach A)
│   └── entrypoint.sh                  # container-internal orchestrator
│
├── harnesses/                         # harness registry (extensible)
│   ├── opencode/
│   │   ├── manifest.yaml
│   │   └── adapter.sh
│   ├── pi/
│   │   ├── manifest.yaml
│   │   └── adapter.sh
│   └── _template/
│       ├── manifest.yaml
│       └── adapter.sh
│
├── benchmark/                         # inspect-ai orchestrator (host-side)
│   ├── __init__.py
│   ├── task_loader.py                 # polyglot exercise -> inspect-ai samples
│   ├── solver.py                      # docker run + container lifecycle
│   ├── scorer.py                      # test run + metric collection
│   ├── store.py                       # SQLite CRUD (idempotent UPSERT)
│   └── report.py                      # leaderboard generation (html/md/json)
│
├── container/                         # container-internal helpers
│   ├── extract-metrics.py             # events.jsonl -> metrics.json (per-format)
│   ├── assemble-prompt.sh             # .docs/ -> prompt.txt
│   ├── run-tests.sh                   # pytest / jest dispatch
│   └── check-tamper.sh                # test file modification check
│
├── scripts/
│   ├── benchmark.sh                   # entry point: ./benchmark.sh [flags]
│   ├── report.sh                      # report generation only
│   ├── build-image.sh                 # docker build
│   └── setup-polyglot.sh              # vendor/clone polyglot-benchmark submodule
│
├── polyglot-benchmark/                # git submodule (Aider-AI/polyglot-benchmark)
│   ├── python/exercises/practice/...
│   └── javascript/exercises/practice/...
│
├── results/                           # .gitignore (store.db committed)
│   ├── store.db                       # <- committed
│   ├── store.db-journal               # <- .gitignore
│   └── artifacts/                     # <- .gitignore (large)
│
└── docs/                              # GitHub Pages source
    ├── index.html                     # leaderboard (generated)
    ├── leaderboard.md                 # markdown mirror
    ├── assets/
    │   └── leaderboard-data.json
    └── superpowers/
        └── specs/
            └── 2026-07-08-harness-benchmark-design.md  (this file)
```

## 11. Reproducibility

### For another developer

```bash
# 1. Clone (submodule included)
git clone --recurse-submodules https://github.com/tufantunc/harness-benchmark.git
cd harness-benchmark

# 2. API key
cp .env.example .env
echo "LLM_API_KEY=sk-..." >> .env

# 3. Build Docker image (once)
./scripts/build-image.sh

# 4. Run (defaults: GLM-5.2, opencode+pi, python+js, 3 repetitions)
./scripts/benchmark.sh

# 5. View results
./scripts/report.sh
# -> docs/index.html in browser
# -> or https://<user>.github.io/harness-benchmark/
```

### Different model

```bash
./scripts/benchmark.sh \
  --model-url https://api.anthropic.com \
  --model-protocol anthropic \
  --model-name claude-sonnet-4-5
```

The store's `UNIQUE(harness, model, language, exercise, repetition)` constraint means different models never collide. The leaderboard filters by model.

### Adding a harness

```bash
cp -r harnesses/_template harnesses/cursor
$EDITOR harnesses/cursor/manifest.yaml    # invocation + setup hook
$EDITOR harnesses/cursor/adapter.sh
$EDITOR docker/Dockerfile                 # add install command
./scripts/build-image.sh
./scripts/benchmark.sh --harnesses cursor --skip-existing
# -> existing opencode/pi scores preserved, cursor added
```

### Polyglot-benchmark sourcing

Git submodule pinned to a specific commit for reproducibility:

```ini
# .gitmodules
[submodule "polyglot-benchmark"]
    path = polyglot-benchmark
    url = https://github.com/Aider-AI/polyglot-benchmark.git
```

`scripts/setup-polyglot.sh` ensures the submodule is initialized and checks out the pinned commit.

## 12. Key Decisions

| Decision | Rationale |
|----------|-----------|
| Single Docker image (Approach A) | Maximal reproducibility, lowest contributor friction |
| inspect-ai on host | Powerful eval framework, Docker spawn for isolation |
| Aider Polyglot (Python+JS MVP) | Agent-agnostic, well-understood, git-worktree-friendly |
| URL-based model config (not provider) | Provider-agnostic, reproducible across endpoints |
| SQLite store (not timestamped folders) | Incremental leaderboard, idempotent UPSERT, queryable |
| Harness registry (manifest+adapter) | New harness without orchestrator changes |
| 3 repetitions default (configurable) | Balance between variance measurement and cost |
| GitHub Pages from /docs | Static leaderboard, auto-updated on push |
| Store committed, artifacts gitignored | Leaderboard continuity without repo bloat |
