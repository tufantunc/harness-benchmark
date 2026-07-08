# harness-benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker-isolated benchmark harness that compares coding agent harnesses (opencode, pi) on Aider Polyglot exercises, with incremental SQLite results store and GitHub Pages leaderboard.

**Architecture:** Single Docker image contains both harnesses + language tooling. A Python orchestrator (inspect-ai types, custom runner) on the host spawns a fresh container per (harness x exercise x repetition), collects metrics via mounted volume, stores in SQLite, and generates leaderboard HTML/MD for GitHub Pages.

**Tech Stack:** Python 3.12, inspect-ai, SQLite, Docker, Bash, Node 22 (opencode/pi inside container), pytest/jest (test suites)

---

## File Structure

```
harness-benchmark/
├── pyproject.toml                      # Python project: inspect-ai, pyyaml, etc.
├── benchmark.yaml                      # main config (model, tasks, run, reporting)
├── .gitmodules                         # polyglot-benchmark submodule
│
├── benchmark/                          # Python package (host-side orchestrator)
│   ├── __init__.py
│   ├── config.py                       # Config dataclass + loader (yaml + .env + CLI)
│   ├── store.py                        # SQLite CRUD (idempotent UPSERT)
│   ├── task_loader.py                  # polyglot exercise discovery -> Sample list
│   ├── runner.py                       # Docker orchestration loop per (harness×task×rep)
│   ├── __main__.py                     # CLI entry point (argparse -> config -> run)
│   └── report.py                       # SQLite query -> HTML/MD/JSON leaderboard
│
├── container/                          # container-internal helpers (baked into image)
│   ├── extract_metrics.py              # events.jsonl -> metrics.json (pi/opencode parsers)
│   ├── assemble_prompt.sh              # .docs/*.md -> prompt.txt
│   ├── run_tests.sh                    # pytest / jest dispatch by language
│   └── check_tamper.sh                 # test file modification detection
│
├── docker/
│   ├── Dockerfile                      # single image: python3+pytest, node22+jest, opencode, pi
│   └── entrypoint.sh                   # container orchestrator (setup->agent->test->collect->emit)
│
├── harnesses/                          # harness registry
│   ├── _template/
│   │   ├── manifest.yaml
│   │   └── adapter.sh
│   ├── opencode/
│   │   ├── manifest.yaml
│   │   └── adapter.sh
│   └── pi/
│       ├── manifest.yaml
│       └── adapter.sh
│
├── scripts/
│   ├── benchmark.sh                    # main entry point
│   ├── report.sh                       # report generation only
│   ├── build-image.sh                  # docker build wrapper
│   └── setup-polyglot.sh               # submodule init + pin
│
├── tests/                              # pytest tests
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_store.py
│   ├── test_extract_metrics.py
│   ├── test_scorer.py
│   ├── test_task_loader.py
│   └── fixtures/
│       ├── pi-events.jsonl
│       ├── opencode-events.jsonl
│       └── sample-exercise/
│           └── ...
│
├── polyglot-benchmark/                 # git submodule
├── results/
│   ├── store.db                        # committed
│   └── .gitkeep
├── docs/                               # GitHub Pages
│   ├── index.html
│   └── assets/
│       └── .gitkeep
└── docs/superpowers/
    ├── specs/
    │   └── 2026-07-08-harness-benchmark-design.md
    └── plans/
        └── 2026-07-08-harness-benchmark.md  (this file)
```

---

## Phase 1: Foundation

### Task 1: Python Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `benchmark/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "harness-benchmark"
version = "0.1.0"
description = "Benchmark coding agent harnesses with identical LLM"
requires-python = ">=3.12"
dependencies = [
    "inspect-ai>=0.3.0",
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[project.scripts]
harness-benchmark = "benchmark.__main__:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools]
packages = ["benchmark", "container"]
```

- [ ] **Step 2: Create package init**

```python
# benchmark/__init__.py
"""harness-benchmark: benchmark coding agent harnesses."""
```

- [ ] **Step 3: Create test init and conftest**

```python
# tests/__init__.py
```

```python
# tests/conftest.py
import os
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR
```

- [ ] **Step 4: Create venv and install**

Run:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```
Expected: packages install successfully.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml benchmark/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: python project skeleton with inspect-ai dependency"
```

---

### Task 2: Config System

**Files:**
- Create: `benchmark/config.py`
- Create: `benchmark.yaml`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from textwrap import dedent

from benchmark.config import Config, load_config


def test_load_config_from_yaml(tmp_path):
    yaml_content = dedent("""
        model:
          url: https://open.bigmodel.cn/api/paas/v4/
          protocol: openai
          name: glm-5.2
          api_key_env: LLM_API_KEY

        task:
          source: polyglot
          languages: [python, javascript]
          addendum: "Don't rename functions."

        run:
          repetitions: 3
          timeout_sec: 600
          skip_existing: true
          parallel: 1

        harnesses: [opencode, pi]

        docker:
          image: harness:latest
          results_volume: ./results

        reporting:
          output: [sqlite, html, markdown]
          pages_path: docs
          auto_commit: true
    """)
    config_file = tmp_path / "benchmark.yaml"
    config_file.write_text(yaml_content)

    config = load_config(config_file)

    assert config.model.url == "https://open.bigmodel.cn/api/paas/v4/"
    assert config.model.protocol == "openai"
    assert config.model.name == "glm-5.2"
    assert config.run.repetitions == 3
    assert config.harnesses == ["opencode", "pi"]
    assert config.task.languages == ["python", "javascript"]


def test_cli_overrides(tmp_path, monkeypatch):
    yaml_content = dedent("""
        model:
          url: https://default.example.com
          protocol: openai
          name: default-model
          api_key_env: LLM_API_KEY
        task:
          source: polyglot
          languages: [python]
          addendum: ""
        run:
          repetitions: 1
          timeout_sec: 300
          skip_existing: false
          parallel: 1
        harnesses: [opencode]
        docker:
          image: harness:latest
          results_volume: ./results
        reporting:
          output: [sqlite]
          pages_path: docs
          auto_commit: false
    """)
    config_file = tmp_path / "benchmark.yaml"
    config_file.write_text(yaml_content)

    config = load_config(
        config_file,
        cli_overrides={"model_url": "https://override.example.com", "repetitions": 5},
    )

    assert config.model.url == "https://override.example.com"
    assert config.run.repetitions == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'benchmark.config'`

- [ ] **Step 3: Write the implementation**

```python
# benchmark/config.py
"""Configuration loading: benchmark.yaml <- .env <- CLI overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ModelConfig:
    url: str = ""
    protocol: str = "openai"
    name: str = ""
    api_key_env: str = "LLM_API_KEY"

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass
class TaskConfig:
    source: str = "polyglot"
    languages: list[str] = field(default_factory=lambda: ["python", "javascript"])
    addendum: str = ""


@dataclass
class RunConfig:
    repetitions: int = 3
    timeout_sec: int = 600
    skip_existing: bool = True
    retry_failed: bool = False
    parallel: int = 1


@dataclass
class DockerConfig:
    image: str = "harness:latest"
    results_volume: str = "./results"


@dataclass
class ReportingConfig:
    output: list[str] = field(default_factory=lambda: ["sqlite", "html", "markdown"])
    pages_path: str = "docs"
    auto_commit: bool = True


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    task: TaskConfig = field(default_factory=TaskConfig)
    run: RunConfig = field(default_factory=RunConfig)
    harnesses: list[str] = field(default_factory=lambda: ["opencode", "pi"])
    docker: DockerConfig = field(default_factory=DockerConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    base_dir: Path = Path(".")


def load_config(
    config_path: Path = Path("benchmark.yaml"),
    cli_overrides: dict | None = None,
) -> Config:
    cli_overrides = cli_overrides or {}
    raw = yaml.safe_load(config_path.read_text()) or {}

    model = ModelConfig(**raw.get("model", {}))
    task = TaskConfig(**raw.get("task", {}))
    run = RunConfig(**raw.get("run", {}))
    docker = DockerConfig(**raw.get("docker", {}))
    reporting = ReportingConfig(**raw.get("reporting", {}))
    harnesses = raw.get("harnesses", ["opencode", "pi"])

    # CLI overrides
    if "model_url" in cli_overrides:
        model.url = cli_overrides["model_url"]
    if "model_protocol" in cli_overrides:
        model.protocol = cli_overrides["model_protocol"]
    if "model_name" in cli_overrides:
        model.name = cli_overrides["model_name"]
    if "repetitions" in cli_overrides:
        run.repetitions = cli_overrides["repetitions"]
    if "timeout_sec" in cli_overrides:
        run.timeout_sec = cli_overrides["timeout_sec"]
    if "harnesses" in cli_overrides:
        harnesses = cli_overrides["harnesses"]
    if "languages" in cli_overrides:
        task.languages = cli_overrides["languages"]
    if "skip_existing" in cli_overrides:
        run.skip_existing = cli_overrides["skip_existing"]
    if "retry_failed" in cli_overrides:
        run.retry_failed = cli_overrides["retry_failed"]

    return Config(
        model=model,
        task=task,
        run=run,
        harnesses=harnesses,
        docker=docker,
        reporting=reporting,
        base_dir=config_path.parent,
    )
```

- [ ] **Step 4: Create the default benchmark.yaml**

```yaml
# benchmark.yaml
model:
  url: https://open.bigmodel.cn/api/paas/v4/
  protocol: openai
  name: glm-5.2
  api_key_env: LLM_API_KEY

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

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add benchmark/config.py benchmark.yaml tests/test_config.py
git commit -m "feat: config system with yaml + CLI overrides"
```

---

### Task 3: Polyglot Submodule + Setup Script

**Files:**
- Create: `.gitmodules`
- Create: `scripts/setup-polyglot.sh`
- Create: `results/.gitkeep`

- [ ] **Step 1: Add polyglot-benchmark as git submodule**

Run:
```bash
git submodule add https://github.com/Aider-AI/polyglot-benchmark.git polyglot-benchmark
```
Expected: `.gitmodules` created, `polyglot-benchmark/` populated.

- [ ] **Step 2: Pin to current HEAD commit (reproducibility)**

Run:
```bash
cd polyglot-benchmark && git log --oneline -1
# Note the commit hash, it's now pinned via submodule
cd ..
git add .gitmodules polyglot-benchmark
git commit -m "chore: add polyglot-benchmark submodule (pinned commit)"
```

- [ ] **Step 3: Create setup-polyglot.sh**

```bash
#!/usr/bin/env bash
# scripts/setup-polyglot.sh — ensure polyglot-benchmark submodule is initialized
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

if [ ! -f polyglot-benchmark/python/exercises/practice/$(ls polyglot-benchmark/python/exercises/practice/ 2>/dev/null | head -1) ]; then
    echo "Initializing polyglot-benchmark submodule..."
    git submodule update --init --recursive
fi

echo "polyglot-benchmark ready."
# Verify exercise counts
PYTHON_COUNT=$(find polyglot-benchmark/python/exercises/practice -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
JS_COUNT=$(find polyglot-benchmark/javascript/exercises/practice -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
echo "Python exercises: $PYTHON_COUNT"
echo "JavaScript exercises: $JS_COUNT"
```

- [ ] **Step 4: Make executable and test**

Run:
```bash
chmod +x scripts/setup-polyglot.sh
./scripts/setup-polyglot.sh
```
Expected: "Python exercises: 34" and "JavaScript exercises: 49"

- [ ] **Step 5: Create results/.gitkeep and commit**

```bash
touch results/.gitkeep
git add scripts/setup-polyglot.sh results/.gitkeep
git commit -m "chore: polyglot setup script + results placeholder"
```

---

## Phase 2: Results Store

### Task 4: SQLite Store

**Files:**
- Create: `benchmark/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
from benchmark.store import Store, RunResult


def test_store_insert_and_query(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()

    result = RunResult(
        run_id="batch-001",
        harness="opencode",
        model="glm-5.2",
        language="python",
        exercise="affine-cipher",
        repetition=1,
        success=True,
        tokens_input=4231,
        tokens_output=567,
        tokens_cached=8900,
        cost_usd=0.021,
        duration_sec=47.3,
        tool_calls=8,
        llm_calls=4,
        diff_loc=42,
        timed_out=False,
        tampered=False,
        artifact_path="artifacts/batch-001/opencode/python/affine-cipher/rep-1",
    )
    store.upsert(result)

    rows = store.query(harness="opencode", model="glm-5.2")
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].cost_usd == 0.021


def test_store_upsert_is_idempotent(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()

    result1 = RunResult(
        run_id="batch-001", harness="pi", model="glm-5.2", language="python",
        exercise="affine-cipher", repetition=1, success=False,
        tokens_input=100, tokens_output=50, tokens_cached=0,
        cost_usd=0.001, duration_sec=10.0, tool_calls=2, llm_calls=1,
        diff_loc=5, timed_out=False, tampered=False, artifact_path="",
    )
    store.upsert(result1)

    result2 = RunResult(
        run_id="batch-002", harness="pi", model="glm-5.2", language="python",
        exercise="affine-cipher", repetition=1, success=True,
        tokens_input=200, tokens_output=80, tokens_cached=0,
        cost_usd=0.002, duration_sec=20.0, tool_calls=3, llm_calls=2,
        diff_loc=10, timed_out=False, tampered=False, artifact_path="",
    )
    store.upsert(result2)

    rows = store.query(harness="pi", model="glm-5.2")
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].cost_usd == 0.002


def test_store_skip_existing_check(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()

    result = RunResult(
        run_id="b1", harness="opencode", model="glm-5.2", language="python",
        exercise="leap", repetition=1, success=True,
        tokens_input=10, tokens_output=5, tokens_cached=0,
        cost_usd=0.001, duration_sec=5.0, tool_calls=1, llm_calls=1,
        diff_loc=3, timed_out=False, tampered=False, artifact_path="",
    )
    store.upsert(result)

    assert store.exists("opencode", "glm-5.2", "python", "leap", 1)
    assert not store.exists("opencode", "glm-5.2", "python", "leap", 2)
    assert not store.exists("pi", "glm-5.2", "python", "leap", 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# benchmark/store.py
"""SQLite results store with idempotent UPSERT."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    run_id: str
    harness: str
    model: str
    language: str
    exercise: str
    repetition: int
    success: bool
    tokens_input: int
    tokens_output: int
    tokens_cached: int
    cost_usd: float
    duration_sec: float
    tool_calls: int
    llm_calls: int
    diff_loc: int
    timed_out: bool
    tampered: bool
    artifact_path: str


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    harness       TEXT NOT NULL,
    model         TEXT NOT NULL,
    language      TEXT NOT NULL,
    exercise      TEXT NOT NULL,
    repetition    INTEGER NOT NULL,
    success       BOOLEAN NOT NULL,
    tokens_input  INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    tokens_cached INTEGER NOT NULL DEFAULT 0,
    cost_usd      REAL NOT NULL DEFAULT 0.0,
    duration_sec  REAL NOT NULL DEFAULT 0.0,
    tool_calls    INTEGER NOT NULL DEFAULT 0,
    llm_calls     INTEGER NOT NULL DEFAULT 0,
    diff_loc      INTEGER NOT NULL DEFAULT 0,
    timed_out     BOOLEAN NOT NULL DEFAULT 0,
    tampered      BOOLEAN NOT NULL DEFAULT 0,
    artifact_path TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(harness, model, language, exercise, repetition)
);
"""


class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    def upsert(self, result: RunResult):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, harness, model, language, exercise, repetition,
                    success, tokens_input, tokens_output, tokens_cached, cost_usd,
                    duration_sec, tool_calls, llm_calls, diff_loc, timed_out, tampered,
                    artifact_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(harness, model, language, exercise, repetition)
                DO UPDATE SET
                    run_id=excluded.run_id,
                    success=excluded.success,
                    tokens_input=excluded.tokens_input,
                    tokens_output=excluded.tokens_output,
                    tokens_cached=excluded.tokens_cached,
                    cost_usd=excluded.cost_usd,
                    duration_sec=excluded.duration_sec,
                    tool_calls=excluded.tool_calls,
                    llm_calls=excluded.llm_calls,
                    diff_loc=excluded.diff_loc,
                    timed_out=excluded.timed_out,
                    tampered=excluded.tampered,
                    artifact_path=excluded.artifact_path,
                    created_at=CURRENT_TIMESTAMP
                """,
                (
                    result.run_id, result.harness, result.model, result.language,
                    result.exercise, result.repetition, result.success,
                    result.tokens_input, result.tokens_output, result.tokens_cached,
                    result.cost_usd, result.duration_sec, result.tool_calls,
                    result.llm_calls, result.diff_loc, result.timed_out,
                    result.tampered, result.artifact_path,
                ),
            )

    def exists(self, harness: str, model: str, language: str, exercise: str, rep: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM runs WHERE harness=? AND model=? AND language=? AND exercise=? AND repetition=?",
                (harness, model, language, exercise, rep),
            ).fetchone()
            return row is not None

    def query(
        self,
        harness: str | None = None,
        model: str | None = None,
        language: str | None = None,
    ) -> list[RunResult]:
        clauses = []
        params = []
        if harness:
            clauses.append("harness = ?")
            params.append(harness)
        if model:
            clauses.append("model = ?")
            params.append(model)
        if language:
            clauses.append("language = ?")
            params.append(language)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM runs{where} ORDER BY harness, language, exercise, repetition",
                params,
            ).fetchall()

        return [
            RunResult(
                run_id=r["run_id"], harness=r["harness"], model=r["model"],
                language=r["language"], exercise=r["exercise"],
                repetition=r["repetition"], success=bool(r["success"]),
                tokens_input=r["tokens_input"], tokens_output=r["tokens_output"],
                tokens_cached=r["tokens_cached"], cost_usd=r["cost_usd"],
                duration_sec=r["duration_sec"], tool_calls=r["tool_calls"],
                llm_calls=r["llm_calls"], diff_loc=r["diff_loc"],
                timed_out=bool(r["timed_out"]), tampered=bool(r["tampered"]),
                artifact_path=r["artifact_path"],
            )
            for r in rows
        ]

    def export_json(self) -> list[dict]:
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM runs ORDER BY harness, model, language, exercise").fetchall()
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_store.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add benchmark/store.py tests/test_store.py
git commit -m "feat: SQLite results store with idempotent UPSERT"
```

---

## Phase 3: Container Infrastructure

### Task 5: Container Shell Helpers

**Files:**
- Create: `container/assemble_prompt.sh`
- Create: `container/run_tests.sh`
- Create: `container/check_tamper.sh`

- [ ] **Step 1: Create assemble_prompt.sh**

```bash
#!/usr/bin/env bash
# container/assemble_prompt.sh
# Assembles the exercise prompt from .docs/ + addendum.
# Usage: assemble_prompt.sh <exercise_dir> <output_file> <addendum_file>
set -euo pipefail

EXERCISE_DIR="$1"
OUTPUT_FILE="$2"
ADDENDUM_FILE="${3:-/dev/null}"

DOCS_DIR="$EXERCISE_DIR/.docs"

{
    # Introduction (optional)
    if [ -f "$DOCS_DIR/introduction.md" ]; then
        cat "$DOCS_DIR/introduction.md"
        echo ""
    fi

    # Main instructions (required)
    cat "$DOCS_DIR/instructions.md"
    echo ""

    # Append (optional)
    if [ -f "$DOCS_DIR/instructions.append.md" ]; then
        cat "$DOCS_DIR/instructions.append.md"
        echo ""
    fi

    # Fixed addendum
    cat "$ADDENDUM_FILE"
} > "$OUTPUT_FILE"
```

- [ ] **Step 2: Create run_tests.sh**

```bash
#!/usr/bin/env bash
# container/run_tests.sh
# Runs the exercise test suite by language.
# Usage: run_tests.sh <language> <workdir> <test_files...>
# Output: test stdout+stderr to stdout, exit code = test exit code
set -euo pipefail

LANGUAGE="$1"
WORKDIR="$2"
shift 2
TEST_FILES=("$@")

cd "$WORKDIR"

case "$LANGUAGE" in
    python)
        for tf in "${TEST_FILES[@]}"; do
            python -m pytest "$tf" --tb=short -q
        done
        ;;
    javascript)
        # Re-enable skipped Exercism tests (xtest -> test)
        sed -i 's/\bxtest(/test(/g' ./*.spec.js 2>/dev/null || true
        npm run test 2>&1
        ;;
    *)
        echo "Unknown language: $LANGUAGE" >&2
        exit 1
        ;;
esac
```

- [ ] **Step 3: Create check_tamper.sh**

```bash
#!/usr/bin/env bash
# container/check_tamper.sh
# Checks if the agent modified any test files.
# Usage: check_tamper.sh <workdir> <test_files...>
# Exit 0 = no tamper, exit 1 = tampered
set -euo pipefail

WORKDIR="$1"
shift
TEST_FILES=("$@")

cd "$WORKDIR"

for tf in "${TEST_FILES[@]}"; do
    if git diff --quiet -- "$tf" 2>/dev/null; then
        :
    else
        echo "TAMPERED: $tf" >&2
        exit 1
    fi
done

exit 0
```

- [ ] **Step 4: Make all executable**

Run: `chmod +x container/*.sh`

- [ ] **Step 5: Commit**

```bash
git add container/assemble_prompt.sh container/run_tests.sh container/check_tamper.sh
git commit -m "feat: container shell helpers (prompt assembly, test runner, tamper check)"
```

---

### Task 6: extract_metrics.py — pi Parser

**Files:**
- Create: `container/extract_metrics.py`
- Create: `tests/test_extract_metrics.py`
- Create: `tests/fixtures/pi-events.jsonl`

- [ ] **Step 1: Create pi fixture**

```
{"type":"session","version":3,"id":"abc-123","timestamp":"2026-07-08T10:00:00.000Z","cwd":"/workdir"}
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"assistant","content":[],"api":"anthropic","provider":"zai","model":"glm-5.2","usage":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"totalTokens":0,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"stop","timestamp":0}}
{"type":"tool_execution_start","toolCallId":"call_1","toolName":"bash","args":{"command":"ls"}}
{"type":"tool_execution_end","toolCallId":"call_1","toolName":"bash","result":{"output":"affine_cipher.py"},"isError":false}
{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"Done!"}],"api":"anthropic","provider":"zai","model":"glm-5.2","usage":{"input":4231,"output":567,"cacheRead":8900,"cacheWrite":200,"totalTokens":13898,"cost":{"input":0.012,"output":0.008,"cacheRead":0.001,"cacheWrite":0.002,"total":0.023}},"stopReason":"stop","timestamp":1752000000000}}
{"type":"turn_end","message":{"role":"assistant","content":[{"type":"text","text":"Done!"}],"provider":"zai","model":"glm-5.2","usage":{"input":4231,"output":567,"cacheRead":8900,"cacheWrite":200,"totalTokens":13898,"cost":{"input":0.012,"output":0.008,"cacheRead":0.001,"cacheWrite":0.002,"total":0.023}},"stopReason":"stop","timestamp":1752000000000},"toolResults":[]}
{"type":"agent_end","messages":[]}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_extract_metrics.py
import json
from pathlib import Path

from container.extract_metrics import extract_metrics, Metrics


def test_extract_pi_events(fixtures_dir):
    events_file = fixtures_dir / "pi-events.jsonl"
    metrics = extract_metrics(events_file, format="pi")

    assert metrics.tokens_input == 4231
    assert metrics.tokens_output == 567
    assert metrics.tokens_cached == 8900
    assert abs(metrics.cost_usd - 0.023) < 0.001
    assert metrics.llm_calls == 2
    assert metrics.tool_calls == 1


def test_extract_empty_events(tmp_path):
    events_file = tmp_path / "empty.jsonl"
    events_file.write_text("")
    metrics = extract_metrics(events_file, format="pi")

    assert metrics.tokens_input == 0
    assert metrics.tokens_output == 0
    assert metrics.cost_usd == 0.0
    assert metrics.llm_calls == 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_extract_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the implementation**

```python
#!/usr/bin/env python3
# container/extract_metrics.py
"""Parse agent JSON event streams and extract normalized metrics."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Metrics:
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cached: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    llm_calls: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def parse_pi_events(lines: list[str]) -> Metrics:
    """Parse pi --mode json output.

    AssistantMessage events contain a 'usage' object with token/cost data.
    tool_execution_start events indicate tool calls.
    """
    m = Metrics()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        if evt.get("type") == "message_end":
            msg = evt.get("message", {})
            if msg.get("role") == "assistant":
                m.llm_calls += 1
                usage = msg.get("usage", {})
                m.tokens_input += usage.get("input", 0)
                m.tokens_output += usage.get("output", 0)
                m.tokens_cached += usage.get("cacheRead", 0)
                cost = usage.get("cost", {})
                m.cost_usd += cost.get("total", 0.0)
                # Count tool calls within this message
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "toolCall":
                        m.tool_calls += 1

        elif evt.get("type") == "tool_execution_start":
            m.tool_calls += 1

    return m


def parse_opencode_events(lines: list[str]) -> Metrics:
    """Parse opencode run --format json output.

    opencode emits JSON events. Token usage may appear in message events.
    Falls back gracefully if usage data is not present.
    """
    m = Metrics()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        evt_type = evt.get("type", "")

        # opencode event types: look for token/usage in various event shapes
        if evt_type in ("message", "message_end", "assistant"):
            usage = evt.get("usage") or evt.get("message", {}).get("usage", {})
            if usage:
                m.llm_calls += 1
                m.tokens_input += usage.get("input_tokens", usage.get("input", 0))
                m.tokens_output += usage.get("output_tokens", usage.get("output", 0))
                m.tokens_cached += usage.get("cache_read_tokens",
                                            usage.get("cached_tokens",
                                            usage.get("cacheRead", 0)))
                cost = usage.get("cost") or usage.get("total_cost", {})
                if isinstance(cost, dict):
                    m.cost_usd += cost.get("total", 0.0)
                elif isinstance(cost, (int, float)):
                    m.cost_usd += cost

        if evt_type in ("tool_start", "tool_call", "tool_execution_start"):
            m.tool_calls += 1

    return m


PARSERS = {
    "pi": parse_pi_events,
    "opencode": parse_opencode_events,
}


def extract_metrics(events_file: Path, format: str) -> Metrics:
    parser = PARSERS.get(format)
    if parser is None:
        raise ValueError(f"Unknown format: {format}. Supported: {list(PARSERS)}")
    lines = events_file.read_text().splitlines()
    return parser(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_metrics.py <events.jsonl> <format> [output.json]", file=sys.stderr)
        sys.exit(1)
    events_file = Path(sys.argv[1])
    fmt = sys.argv[2]
    output = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    metrics = extract_metrics(events_file, fmt)
    result = metrics.to_dict()

    if output:
        output.write_text(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Create container package init for testing**

```python
# container/__init__.py
"""Container-internal helpers (also importable for testing)."""
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_extract_metrics.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add container/extract_metrics.py container/__init__.py tests/test_extract_metrics.py tests/fixtures/pi-events.jsonl
git commit -m "feat: extract_metrics.py with pi event parser"
```

---

### Task 7: Dockerfile + entrypoint.sh

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/entrypoint.sh`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# docker/Dockerfile — single image with all tooling
FROM node:22-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git jq curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python testing tools
RUN python3 -m pip install --break-system-packages pytest

# JavaScript testing dependencies (shared node_modules for jest + babel)
RUN mkdir -p /npm-install
WORKDIR /npm-install
RUN npm init -y && \
    npm install jest@29.7.0 @babel/core @exercism/babel-preset-javascript && \
    echo '{"presets":["@exercism/babel-preset-javascript"]}' > babel.config.js

# Install harness CLIs globally
RUN npm install -g opencode-ai && \
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent

# Copy container helpers
COPY container/ /app/container/
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/container/*.sh

# Copy polyglot-benchmark data (baked in, read-only)
COPY polyglot-benchmark/ /app/polyglot-benchmark/

# Copy harness adapters
COPY harnesses/ /app/harnesses/

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
```

- [ ] **Step 2: Create entrypoint.sh**

```bash
#!/usr/bin/env bash
# docker/entrypoint.sh
# Container-internal orchestrator for a single (harness x exercise x rep).
#
# Usage: entrypoint.sh <harness> <exercise_relpath> <rep> <results_dir>
# Env:   MODEL_URL, PROTOCOL, MODEL_NAME, LLM_API_KEY (or $api_key_env), TASK_TIMEOUT
set -euo pipefail

HARNESS="$1"
EXERCISE_REL="$2"          # e.g. python/exercises/practice/affine-cipher
REP="$3"
RESULTS_DIR="$4"           # mounted volume for artifacts

POLYGLOT="/app/polyglot-benchmark"
EXERCISE_SRC="$POLYGLOT/$EXERCISE_REL"
WORKDIR="/workdir"
OUTPUT="/output"

mkdir -p "$WORKDIR" "$OUTPUT"
cd "$WORKDIR"
git init -q 2>/dev/null || true
git add -A && git commit -q -m "init" --allow-empty 2>/dev/null || true

# --- 1. SETUP: copy exercise stub (no test files) ---
CONFIG_JSON="$EXERCISE_SRC/.meta/config.json"
SOLUTION_FILES=$(jq -r '.files.solution[]' "$CONFIG_JSON")
TEST_FILES=$(jq -r '.files.test[]' "$CONFIG_JSON")

# Copy solution (stub) files
for f in $SOLUTION_FILES; do
    mkdir -p "$(dirname "$WORKDIR/$f")"
    cp "$EXERCISE_SRC/$f" "$WORKDIR/$f"
done

# Copy .docs/ (instructions)
cp -r "$EXERCISE_SRC/.docs" "$WORKDIR/.docs"

# Copy config.json for reference
mkdir -p "$WORKDIR/.meta"
cp "$CONFIG_JSON" "$WORKDIR/.meta/config.json"

# For JS: copy package.json, babel config, etc.
LANGUAGE=$(echo "$EXERCISE_REL" | cut -d/ -f1)
if [ "$LANGUAGE" = "javascript" ]; then
    for f in package.json babel.config.js .eslintrc .npmrc; do
        [ -f "$EXERCISE_SRC/$f" ] && cp "$EXERCISE_SRC/$f" "$WORKDIR/$f"
    done
fi

git add -A && git commit -q -m "exercise setup" 2>/dev/null || true

# --- 2. SETUP HOOK: generate harness-specific provider config ---
HARNESS_DIR="/app/harnesses/$HARNESS"
MANIFEST="$HARNESS_DIR/manifest.yaml"

# Export model env vars for setup hook
export MODEL_URL PROTOCOL MODEL_NAME
export API_KEY="${LLM_API_KEY:-}"

SETUP_SCRIPT=$(jq -r '.setup // empty' "$MANIFEST" 2>/dev/null || true)
if [ -n "$SETUP_SCRIPT" ]; then
    eval "$SETUP_SCRIPT"
fi

# --- 3. PROMPT ASSEMBLE ---
ADDENDUM_FILE="/tmp/addendum.txt"
echo "Modify only the supplied files. Don't rename functions or classes. Only use standard libraries. Don't install packages." > "$ADDENDUM_FILE"
/app/container/assemble_prompt.sh "$WORKDIR" "$WORKDIR/prompt.txt" "$ADDENDUM_FILE"

# --- 4. AGENT INVOKE ---
MODEL_FLAG=$(jq -r '.invoke.model_flag // "--model benchmark/\$MODEL_NAME"' "$MANIFEST" 2>/dev/null || echo "--model benchmark/\$MODEL_NAME")
MODEL_FLAG=$(eval echo "$MODEL_FLAG")

ADAPTER="$HARNESS_DIR/adapter.sh"
START_TIME=$(date +%s)

set +e
timeout "${TASK_TIMEOUT:-600}" "$ADAPTER" "$WORKDIR/prompt.txt" "$WORKDIR" "$MODEL_FLAG" \
    > "$OUTPUT/events.jsonl" 2> "$OUTPUT/agent-stderr.log"
AGENT_EXIT=$?
set -e

END_TIME=$(date +%s)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
TIMED_OUT=0
if [ "$AGENT_EXIT" = 124 ]; then
    TIMED_OUT=1
fi

# --- 5. TEST RUN: copy test files, run suite ---
for f in $TEST_FILES; do
    mkdir -p "$(dirname "$WORKDIR/$f")"
    cp "$EXERCISE_SRC/$f" "$WORKDIR/$f"
done

set +e
/app/container/run_tests.sh "$LANGUAGE" "$WORKDIR" $TEST_FILES > "$OUTPUT/test-output.txt" 2>&1
TEST_EXIT=$?
set -e

# --- 6. COLLECT ---
git diff --no-color > "$OUTPUT/diff.patch" 2>/dev/null || true
DIFF_LOC=$(git diff --shortstat 2>/dev/null | grep -oP '\d+(?= insertion)' || echo "0")

# Tamper check
set +e
/app/container/check_tamper.sh "$WORKDIR" $TEST_FILES > "$OUTPUT/tamper-check.txt" 2>&1
TAMPER_EXIT=$?
set -e
TAMPERED=$([ "$TAMPER_EXIT" = "1" ] && echo "true" || echo "false")

# Metrics from events
METRIC_FORMAT=$(jq -r '.metric_format // "pi"' "$MANIFEST" 2>/dev/null || echo "pi")
python3 /app/container/extract_metrics.py "$OUTPUT/events.jsonl" "$METRIC_FORMAT" "$OUTPUT/parsed-metrics.json" 2>/dev/null || \
    echo '{"tokens_input":0,"tokens_output":0,"tokens_cached":0,"cost_usd":0.0,"tool_calls":0,"llm_calls":0}' > "$OUTPUT/parsed-metrics.json"

# --- 7. EMIT metrics.json to stdout ---
EXERCISE_NAME=$(basename "$EXERCISE_REL")
python3 -c "
import json, sys
parsed = json.load(open('$OUTPUT/parsed-metrics.json'))
result = {
    'harness': '$HARNESS',
    'model': '$MODEL_NAME',
    'language': '$LANGUAGE',
    'exercise': '$EXERCISE_NAME',
    'repetition': $REP,
    'success': $( [ "$TEST_EXIT" = "0" ] && [ "$TAMPER_EXIT" = "0" ] && echo "True" || echo "False" ),
    'test_exit_code': $TEST_EXIT,
    'agent_exit_code': $AGENT_EXIT,
    'timed_out': $TIMED_OUT,
    'tampered': $TAMPERED,
    'tokens_input': parsed.get('tokens_input', 0),
    'tokens_output': parsed.get('tokens_output', 0),
    'tokens_cached': parsed.get('tokens_cached', 0),
    'cost_usd': parsed.get('cost_usd', 0.0),
    'tool_calls': parsed.get('tool_calls', 0),
    'llm_calls': parsed.get('llm_calls', 0),
    'duration_sec': $DURATION,
    'diff_loc': $DIFF_LOC,
}
print(json.dumps(result))
"

# --- 8. Copy artifacts to mounted volume ---
ARTIFACT_DIR="$RESULTS_DIR/artifacts/$HARNESS/$LANGUAGE/$EXERCISE_NAME/rep-$REP"
mkdir -p "$ARTIFACT_DIR"
cp -r "$OUTPUT/"* "$ARTIFACT_DIR/" 2>/dev/null || true
```

- [ ] **Step 3: Make entrypoint executable**

Run: `chmod +x docker/entrypoint.sh`

- [ ] **Step 4: Commit**

```bash
git add docker/Dockerfile docker/entrypoint.sh
git commit -m "feat: Dockerfile and container entrypoint orchestrator"
```

---

## Phase 4: Harness Adapters

### Task 8: Template Harness

**Files:**
- Create: `harnesses/_template/manifest.yaml`
- Create: `harnesses/_template/adapter.sh`

- [ ] **Step 1: Create manifest template**

```yaml
# harnesses/_template/manifest.yaml
# Copy this directory to harnesses/<your-harness>/ and customize.
name: template
version: "0.0.0"
install: npm install -g your-harness-package

invoke:
  command: your-harness run "$PROMPT" --json --workdir "$WORKDIR"
  model_flag: --model benchmark/$MODEL_NAME

# Setup hook: generates provider config from MODEL_URL, PROTOCOL, MODEL_NAME, API_KEY
setup: |
  echo "Add setup logic here to create provider config for your harness"

metric_source: events.jsonl
metric_format: pi    # 'pi' or 'opencode' — selects the parser in extract_metrics.py
```

- [ ] **Step 2: Create adapter template**

```bash
#!/usr/bin/env bash
# harnesses/_template/adapter.sh
# Invoked by entrypoint.sh with: $1=prompt-file  $2=workdir  $3=model-flag
# Must write JSON events to /output/events.jsonl and exit.
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

# Customize: invoke your harness CLI here
# Must produce JSON event stream on stdout
your-harness run "$PROMPT" \
    $MODEL_FLAG \
    --workdir "$WORKDIR" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x harnesses/_template/adapter.sh
git add harnesses/_template/
git commit -m "feat: harness template for new adapter scaffolding"
```

---

### Task 9: opencode Adapter

**Files:**
- Create: `harnesses/opencode/manifest.yaml`
- Create: `harnesses/opencode/adapter.sh`

- [ ] **Step 1: Create opencode manifest**

```yaml
# harnesses/opencode/manifest.yaml
name: opencode
version: "0.1.48"
install: npm install -g opencode-ai

invoke:
  command: opencode run "$PROMPT" --format json --dir "$WORKDIR" --auto
  model_flag: --model benchmark/$MODEL_NAME

setup: |
  # Generate opencode config with custom provider pointing to MODEL_URL
  mkdir -p "$WORKDIR"
  cat > "$WORKDIR/opencode.json" <<OCEOF
  {
    "provider": {
      "benchmark": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "benchmark",
        "options": {
          "baseURL": "$MODEL_URL",
          "apiKey": "$API_KEY"
        },
        "models": {
          "$MODEL_NAME": {
            "name": "$MODEL_NAME"
          }
        }
      }
    }
  }
  OCEOF

metric_source: events.jsonl
metric_format: opencode
```

- [ ] **Step 2: Create opencode adapter**

```bash
#!/usr/bin/env bash
# harnesses/opencode/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

# opencode run with JSON event output
opencode run "$PROMPT" \
    --format json \
    $MODEL_FLAG \
    --dir "$WORKDIR" \
    --auto \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x harnesses/opencode/adapter.sh
git add harnesses/opencode/
git commit -m "feat: opencode harness adapter and manifest"
```

---

### Task 10: pi Adapter

**Files:**
- Create: `harnesses/pi/manifest.yaml`
- Create: `harnesses/pi/adapter.sh`

- [ ] **Step 1: Create pi manifest**

```yaml
# harnesses/pi/manifest.yaml
name: pi
version: "latest"
install: npm install -g --ignore-scripts @earendil-works/pi-coding-agent

invoke:
  command: pi -p "$PROMPT" --mode json --cwd "$WORKDIR"
  model_flag: --model benchmark/$MODEL_NAME

setup: |
  # Generate pi's models.json with custom provider
  mkdir -p "$WORKDIR/.pi"
  cat > "$WORKDIR/.pi/models.json" <<PIEOF
  {
    "providers": {
      "benchmark": {
        "name": "benchmark",
        "protocol": "$PROTOCOL",
        "baseUrl": "$MODEL_URL",
        "apiKey": "$API_KEY",
        "models": {
          "$MODEL_NAME": {
            "name": "$MODEL_NAME"
          }
        }
      }
    }
  }
  PIEOF

metric_source: events.jsonl
metric_format: pi
```

- [ ] **Step 2: Create pi adapter**

```bash
#!/usr/bin/env bash
# harnesses/pi/adapter.sh
# $1=prompt-file  $2=workdir  $3=model-flag
set -euo pipefail

PROMPT_FILE="$1"
WORKDIR="$2"
MODEL_FLAG="$3"
PROMPT=$(cat "$PROMPT_FILE")

# pi in print/JSON mode
pi -p "$PROMPT" \
    --mode json \
    $MODEL_FLAG \
    --cwd "$WORKDIR" \
    > /output/events.jsonl 2>/output/agent-stderr.log

echo $? > /output/agent-exit-code
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x harnesses/pi/adapter.sh
git add harnesses/pi/
git commit -m "feat: pi harness adapter and manifest"
```

---

## Phase 5: Host Orchestrator

### Task 11: task_loader.py

**Files:**
- Create: `benchmark/task_loader.py`
- Create: `tests/test_task_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_task_loader.py
from benchmark.task_loader import Exercise, load_exercises


def test_load_exercises(tmp_path):
    # Create a minimal polyglot structure
    polyglot = tmp_path / "polyglot-benchmark"
    py_practice = polyglot / "python" / "exercises" / "practice"
    py_practice.mkdir(parents=True)

    exercise = py_practice / "leap"
    exercise.mkdir()
    (exercise / ".docs").mkdir()
    (exercise / ".docs" / "instructions.md").write_text("Implement leap year.")
    (exercise / ".meta").mkdir()
    (exercise / ".meta" / "config.json").write_text(
        '{"files": {"solution": ["leap.py"], "test": ["leap_test.py"], "example": [".meta/example.py"]}}'
    )
    (exercise / "leap.py").write_text("def leap_year(year):\n    pass\n")

    exercises = load_exercises(polyglot, languages=["python"])

    assert len(exercises) == 1
    assert exercises[0].name == "leap"
    assert exercises[0].language == "python"
    assert exercises[0].solution_files == ["leap.py"]
    assert exercises[0].test_files == ["leap_test.py"]
    assert "leap.py" in exercises[0].relpath


def test_load_exercises_filters_language(tmp_path):
    polyglot = tmp_path / "polyglot-benchmark"
    for lang in ["python", "javascript"]:
        practice = polyglot / lang / "exercises" / "practice" / "test-ex"
        practice.mkdir(parents=True)
        (practice / ".docs").mkdir()
        (practice / ".docs" / "instructions.md").write_text("Do something.")
        (practice / ".meta").mkdir()
        ext = ".py" if lang == "python" else ".js"
        test_ext = "_test.py" if lang == "python" else ".spec.js"
        (practice / ".meta" / "config.json").write_text(
            f'{{"files": {{"solution": ["test-ex{ext}"], "test": ["test-ex{test_ext}"]}}}}'
        )
        (practice / f"test-ex{ext}").write_text("pass")

    only_python = load_exercises(polyglot, languages=["python"])
    assert len(only_python) == 1
    assert only_python[0].language == "python"

    both = load_exercises(polyglot, languages=["python", "javascript"])
    assert len(both) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_loader.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# benchmark/task_loader.py
"""Load polyglot-benchmark exercises into structured Exercise objects."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Exercise:
    name: str
    language: str
    relpath: str          # relative to polyglot root, e.g. python/exercises/practice/leap
    solution_files: list[str]
    test_files: list[str]
    instructions_path: Path
    exercise_dir: Path


def load_exercises(
    polyglot_root: Path,
    languages: list[str] | None = None,
) -> list[Exercise]:
    """Discover all exercises under <lang>/exercises/practice/."""
    languages = languages or ["python", "javascript"]
    exercises: list[Exercise] = []

    for lang in languages:
        practice_dir = polyglot_root / lang / "exercises" / "practice"
        if not practice_dir.exists():
            continue

        for exercise_dir in sorted(practice_dir.iterdir()):
            if not exercise_dir.is_dir():
                continue

            config_path = exercise_dir / ".meta" / "config.json"
            instructions_path = exercise_dir / ".docs" / "instructions.md"

            if not config_path.exists() or not instructions_path.exists():
                continue

            config = json.loads(config_path.read_text())
            files = config.get("files", {})

            exercises.append(Exercise(
                name=exercise_dir.name,
                language=lang,
                relpath=str(exercise_dir.relative_to(polyglot_root)),
                solution_files=files.get("solution", []),
                test_files=files.get("test", []),
                instructions_path=instructions_path,
                exercise_dir=exercise_dir,
            ))

    return exercises
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_task_loader.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add benchmark/task_loader.py tests/test_task_loader.py
git commit -m "feat: polyglot exercise loader"
```

---

### Task 12: runner.py (Docker Orchestration)

**Files:**
- Create: `benchmark/runner.py`
- Create: `benchmark/__main__.py`

- [ ] **Step 1: Write runner.py**

```python
# benchmark/runner.py
"""Docker orchestration: spawn one container per (harness x exercise x rep)."""
from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .store import Store, RunResult
from .task_loader import Exercise


@dataclass
class RunOutcome:
    metrics: dict
    skipped: bool = False


def run_single(
    config: Config,
    harness: str,
    exercise: Exercise,
    repetition: int,
    run_id: str,
) -> RunOutcome:
    """Run one (harness x exercise x rep) in a Docker container."""
    store = Store(Path(config.docker.results_volume) / "store.db")
    store.init_schema()

    # Skip if already done and skip_existing is set
    if config.run.skip_existing and store.exists(
        harness, config.model.name, exercise.language, exercise.name, repetition
    ):
        return RunOutcome(metrics={}, skipped=True)

    image = config.docker.image
    results_vol = str(Path(config.docker.results_volume).resolve())

    env = [
        "-e", f"MODEL_URL={config.model.url}",
        "-e", f"PROTOCOL={config.model.protocol}",
        "-e", f"MODEL_NAME={config.model.name}",
        "-e", f"{config.model.api_key_env}={config.model.api_key}",
        "-e", f"TASK_TIMEOUT={config.run.timeout_sec}",
    ]

    cmd = [
        "docker", "run", "--rm",
        *env,
        "-v", f"{results_vol}:/results",
        image,
        harness,
        exercise.relpath,
        str(repetition),
        "/results",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.run.timeout_sec + 120)

    if result.returncode != 0:
        metrics = {
            "harness": harness,
            "model": config.model.name,
            "language": exercise.language,
            "exercise": exercise.name,
            "repetition": repetition,
            "success": False,
            "test_exit_code": -1,
            "agent_exit_code": result.returncode,
            "timed_out": True,
            "tampered": False,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_cached": 0,
            "cost_usd": 0.0,
            "tool_calls": 0,
            "llm_calls": 0,
            "duration_sec": config.run.timeout_sec,
            "diff_loc": 0,
        }
    else:
        try:
            metrics = json.loads(result.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            metrics = {
                "harness": harness, "model": config.model.name,
                "language": exercise.language, "exercise": exercise.name,
                "repetition": repetition, "success": False,
                "test_exit_code": -1, "agent_exit_code": 0,
                "timed_out": False, "tampered": False,
                "tokens_input": 0, "tokens_output": 0, "tokens_cached": 0,
                "cost_usd": 0.0, "tool_calls": 0, "llm_calls": 0,
                "duration_sec": 0.0, "diff_loc": 0,
            }

    # Store result
    run_result = RunResult(
        run_id=run_id,
        harness=harness,
        model=config.model.name,
        language=exercise.language,
        exercise=exercise.name,
        repetition=repetition,
        success=metrics.get("success", False),
        tokens_input=metrics.get("tokens_input", 0),
        tokens_output=metrics.get("tokens_output", 0),
        tokens_cached=metrics.get("tokens_cached", 0),
        cost_usd=metrics.get("cost_usd", 0.0),
        duration_sec=metrics.get("duration_sec", 0.0),
        tool_calls=metrics.get("tool_calls", 0),
        llm_calls=metrics.get("llm_calls", 0),
        diff_loc=metrics.get("diff_loc", 0),
        timed_out=metrics.get("timed_out", False),
        tampered=metrics.get("tampered", False),
        artifact_path=f"artifacts/{harness}/{exercise.language}/{exercise.name}/rep-{repetition}",
    )
    store.upsert(run_result)

    return RunOutcome(metrics=metrics)


def run_benchmark(config: Config, exercises: list[Exercise]) -> dict:
    """Run the full benchmark: all harnesses x all exercises x repetitions."""
    run_id = str(uuid.uuid4())[:8]
    total = len(config.harnesses) * len(exercises) * config.run.repetitions
    completed = 0
    skipped = 0
    failed = 0

    print(f"Starting benchmark run {run_id}")
    print(f"  Harnesses: {config.harnesses}")
    print(f"  Model: {config.model.name} ({config.model.url})")
    print(f"  Exercises: {len(exercises)}")
    print(f"  Repetitions: {config.run.repetitions}")
    print(f"  Total runs: {total}")
    print()

    for harness in config.harnesses:
        for exercise in exercises:
            for rep in range(1, config.run.repetitions + 1):
                completed += 1
                print(f"[{completed}/{total}] {harness}/{exercise.language}/{exercise.name} rep-{rep}", end=" ... ")

                outcome = run_single(config, harness, exercise, rep, run_id)

                if outcome.skipped:
                    print("SKIP (exists)")
                    skipped += 1
                elif outcome.metrics.get("success"):
                    print("PASS")
                else:
                    print("FAIL")
                    failed += 1

    print()
    print(f"Done: {completed - skipped} ran, {skipped} skipped, {failed} failed")
    return {"run_id": run_id, "total": total, "skipped": skipped, "failed": failed}
```

- [ ] **Step 2: Write __main__.py entry point**

```python
# benchmark/__main__.py
"""CLI entry point for harness-benchmark."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .task_loader import load_exercises
from .runner import run_benchmark
from .report import generate_report


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark coding agent harnesses")
    parser.add_argument("--config", default="benchmark.yaml", help="Config file path")
    parser.add_argument("--model-url", dest="model_url", help="Override model endpoint URL")
    parser.add_argument("--model-protocol", dest="model_protocol", help="Override API protocol")
    parser.add_argument("--model-name", dest="model_name", help="Override model name")
    parser.add_argument("--harnesses", help="Comma-separated harness list (e.g. opencode,pi)")
    parser.add_argument("--languages", help="Comma-separated languages (e.g. python,javascript)")
    parser.add_argument("--repetitions", type=int, help="Repetitions per task")
    parser.add_argument("--timeout-sec", dest="timeout_sec", type=int, help="Per-task timeout")
    parser.add_argument("--skip-existing", dest="skip_existing", action="store_true", default=None)
    parser.add_argument("--retry-failed", dest="retry_failed", action="store_true", default=None)
    parser.add_argument("--report-only", dest="report_only", action="store_true", help="Generate report only")
    return parser.parse_args()


def main():
    args = parse_args()

    cli_overrides = {}
    if args.model_url:
        cli_overrides["model_url"] = args.model_url
    if args.model_protocol:
        cli_overrides["model_protocol"] = args.model_protocol
    if args.model_name:
        cli_overrides["model_name"] = args.model_name
    if args.harnesses:
        cli_overrides["harnesses"] = args.harnesses.split(",")
    if args.languages:
        cli_overrides["languages"] = args.languages.split(",")
    if args.repetitions:
        cli_overrides["repetitions"] = args.repetitions
    if args.timeout_sec:
        cli_overrides["timeout_sec"] = args.timeout_sec
    if args.skip_existing is not None:
        cli_overrides["skip_existing"] = args.skip_existing
    if args.retry_failed is not None:
        cli_overrides["retry_failed"] = args.retry_failed

    config = load_config(Path(args.config), cli_overrides)

    if args.report_only:
        generate_report(config)
        return 0

    # Load exercises
    polyglot_root = Path("polyglot-benchmark")
    exercises = load_exercises(polyglot_root, config.task.languages)
    print(f"Loaded {len(exercises)} exercises")

    # Run benchmark
    summary = run_benchmark(config, exercises)

    # Generate report
    generate_report(config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Commit**

```bash
git add benchmark/runner.py benchmark/__main__.py
git commit -m "feat: Docker runner orchestration and CLI entry point"
```

---

## Phase 6: Reporting

### Task 13: report.py (Leaderboard Generation)

**Files:**
- Create: `benchmark/report.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
import json
from pathlib import Path

from benchmark.store import Store, RunResult
from benchmark.report import compute_leaderboard, generate_markdown


def _seed(store: Store, harness: str, success: bool, cost: float, tokens: int):
    store.upsert(RunResult(
        run_id="t1", harness=harness, model="glm-5.2", language="python",
        exercise="test-ex", repetition=1, success=success,
        tokens_input=tokens, tokens_output=0, tokens_cached=0,
        cost_usd=cost, duration_sec=10.0, tool_calls=5, llm_calls=3,
        diff_loc=20, timed_out=False, tampered=False, artifact_path="",
    ))


def test_compute_leaderboard(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()
    _seed(store, "opencode", True, 0.01, 5000)
    _seed(store, "pi", False, 0.02, 8000)

    lb = compute_leaderboard(store, model="glm-5.2")

    assert len(lb) == 2
    # opencode should rank first (100% success)
    assert lb[0]["harness"] == "opencode"
    assert lb[0]["success_rate"] == 1.0
    assert lb[1]["harness"] == "pi"
    assert lb[1]["success_rate"] == 0.0


def test_generate_markdown(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()
    _seed(store, "opencode", True, 0.01, 5000)
    _seed(store, "pi", True, 0.02, 8000)

    lb = compute_leaderboard(store, model="glm-5.2")
    md = generate_markdown(lb, model="glm-5.2")

    assert "| opencode |" in md
    assert "| pi |" in md
    assert "glm-5.2" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# benchmark/report.py
"""Generate leaderboard reports (HTML, Markdown, JSON) from SQLite store."""
from __future__ import annotations

import json
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

from .config import Config
from .store import Store


def compute_leaderboard(store: Store, model: str | None = None, language: str | None = None) -> list[dict]:
    """Aggregate results per harness, return sorted leaderboard rows."""
    rows = store.query(model=model, language=language)

    by_harness: dict[str, list] = defaultdict(list)
    for r in rows:
        by_harness[r.harness].append(r)

    entries = []
    for harness, results in by_harness.items():
        total = len(results)
        successes = [r for r in results if r.success]
        success_rate = len(successes) / total if total > 0 else 0.0

        # pass@k: for each exercise, did at least 1 rep succeed?
        by_exercise: dict[str, list[bool]] = defaultdict(list)
        for r in results:
            by_exercise[r.exercise].append(r.success)
        pass_at_k = sum(1 for ex, vals in by_exercise.items() if any(vals)) / len(by_exercise) if by_exercise else 0.0

        costs = [r.cost_usd for r in successes] if successes else [0.0]
        tokens = [r.tokens_input + r.tokens_output for r in successes] if successes else [0]
        durations = [r.duration_sec for r in results] if results else [0.0]
        tool_calls = [r.tool_calls for r in results] if results else [0]

        entries.append({
            "harness": harness,
            "total_tasks": total,
            "success_rate": round(success_rate, 4),
            "pass_at_k": round(pass_at_k, 4),
            "avg_cost_per_task": round(statistics.mean(costs), 4) if costs else 0.0,
            "tokens_per_success": round(statistics.mean(tokens)) if tokens else 0,
            "avg_duration": round(statistics.mean(durations), 1) if durations else 0.0,
            "avg_tool_calls": round(statistics.mean(tool_calls), 1) if tool_calls else 0.0,
        })

    # Sort by tie-breaker: success_rate desc, tokens_per_success asc, cost asc, duration asc
    entries.sort(key=lambda e: (
        -e["success_rate"],
        e["tokens_per_success"],
        e["avg_cost_per_task"],
        e["avg_duration"],
    ))

    # Add rank
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return entries


def generate_markdown(leaderboard: list[dict], model: str) -> str:
    lines = [
        f"# Leaderboard — {model}",
        "",
        f"| Rank | Harness | Tasks | Success | pass@k | Tokens/Success | Cost/Task | Avg Time | Avg Tools |",
        f"|------|---------|-------|---------|--------|----------------|-----------|----------|-----------|",
    ]
    for e in leaderboard:
        lines.append(
            f"| {e['rank']} | {e['harness']} | {e['total_tasks']} | "
            f"{e['success_rate']:.1%} | {e['pass_at_k']:.1%} | "
            f"{e['tokens_per_success']:,} | ${e['avg_cost_per_task']:.4f} | "
            f"{e['avg_duration']:.0f}s | {e['avg_tool_calls']:.1f} |"
        )
    lines.append("")
    return "\n".join(lines)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>harness-benchmark — Leaderboard</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.6rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  .rank-1 {{ font-weight: bold; }}
  .muted {{ color: #666; }}
  .controls {{ margin: 1rem 0; }}
  select {{ padding: 0.25rem 0.5rem; }}
</style>
</head>
<body>
<h1>harness-benchmark</h1>
<p class="muted">Coding agent harness comparison. <a href="https://github.com/tufantunc/harness-benchmark">Repository</a></p>

<div class="controls">
  <label>Model: <select id="model-select" onchange="filter()"></select></label>
  <label>Language: <select id="lang-select" onchange="filter()">
    <option value="">All</option>
    <option value="python">Python</option>
    <option value="javascript">JavaScript</option>
  </select></label>
</div>

<div id="leaderboard"></div>

<script>
const DATA = {data};

function render(model, lang) {{
  const filtered = DATA.filter(e => (!model || e.model === model) && (!lang || e.language === lang));
  // Aggregate per harness
  const byHarness = {{}};
  filtered.forEach(e => {{
    if (!byHarness[e.harness]) byHarness[e.harness] = [];
    byHarness[e.harness].push(e);
  }});
  const rows = Object.entries(byHarness).map(([harness, items]) => {{
    const total = items.length;
    const succ = items.filter(i => i.success).length;
    return {{
      harness, total,
      success_rate: total ? (succ / total) : 0,
      avg_cost: total ? (items.reduce((s,i) => s + i.cost_usd, 0) / total) : 0,
      avg_tokens: total ? Math.round(items.reduce((s,i) => s + i.tokens_input + i.tokens_output, 0) / total) : 0,
      avg_duration: total ? Math.round(items.reduce((s,i) => s + i.duration_sec, 0) / total) : 0,
    }};
  }});
  rows.sort((a, b) => b.success_rate - a.success_rate || a.avg_tokens - b.avg_tokens);

  let html = '<table><thead><tr><th>Rank</th><th>Harness</th><th>Tasks</th><th>Success</th><th>Tokens/Run</th><th>Cost/Run</th><th>Avg Time</th></tr></thead><tbody>';
  rows.forEach((r, i) => {{
    html += `<tr class="${{i === 0 ? 'rank-1' : ''}}"><td>${{i+1}}</td><td>${{r.harness}}</td><td>${{r.total}}</td><td>${{(r.success_rate*100).toFixed(1)}}%</td><td>${{r.avg_tokens.toLocaleString()}}</td><td>$${{r.avg_cost.toFixed(4)}}</td><td>${{r.avg_duration}}s</td></tr>`;
  }});
  html += '</tbody></table>';
  if (rows.length === 0) html = '<p class="muted">No data for this filter.</p>';
  document.getElementById('leaderboard').innerHTML = html;
}}

function filter() {{
  render(document.getElementById('model-select').value, document.getElementById('lang-select').value);
}}

// Populate model dropdown
const models = [...new Set(DATA.map(e => e.model))];
models.forEach(m => {{
  const opt = document.createElement('option');
  opt.value = m; opt.textContent = m;
  document.getElementById('model-select').appendChild(opt);
}});

// Default: first model
if (models.length > 0) {{
  document.getElementById('model-select').value = models[0];
  render(models[0], '');
}} else {{
  render('', '');
}}
</script>
</body>
</html>"""


def generate_report(config: Config):
    """Generate all report formats and optionally commit."""
    store = Store(Path(config.docker.results_volume) / "store.db")
    store.init_schema()

    raw_data = store.export_json()
    pages_path = Path(config.reporting.pages_path)
    pages_path.mkdir(parents=True, exist_ok=True)

    # JSON data
    assets_dir = pages_path / "assets"
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "leaderboard-data.json").write_text(json.dumps(raw_data, indent=2))

    # HTML
    html = HTML_TEMPLATE.format(data=json.dumps(raw_data))
    (pages_path / "index.html").write_text(html)

    # Markdown
    if raw_data:
        models = sorted(set(r["model"] for r in raw_data))
        md_parts = []
        for model in models:
            lb = compute_leaderboard(store, model=model)
            md_parts.append(generate_markdown(lb, model))
        (pages_path / "leaderboard.md").write_text("\n\n---\n\n".join(md_parts))

    print(f"Report generated in {pages_path}/")

    # Auto-commit
    if config.reporting.auto_commit:
        try:
            subprocess.run(["git", "add", str(pages_path / "index.html"),
                           str(pages_path / "leaderboard.md"),
                           str(assets_dir / "leaderboard-data.json"),
                           str(Path(config.docker.results_volume) / "store.db")],
                          check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m",
                           f"benchmark: update leaderboard ({len(raw_data)} results)"],
                          check=True, capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("Committed and pushed to GitHub (Pages will auto-update)")
        except subprocess.CalledProcessError as e:
            print(f"Warning: git commit/push failed: {e.stderr.decode() if e.stderr else e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_report.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add benchmark/report.py tests/test_report.py
git commit -m "feat: leaderboard report generation (HTML, Markdown, JSON)"
```

---

## Phase 7: Scripts & Integration

### Task 14: Shell Scripts

**Files:**
- Create: `scripts/benchmark.sh`
- Create: `scripts/report.sh`
- Create: `scripts/build-image.sh`

- [ ] **Step 1: Create build-image.sh**

```bash
#!/usr/bin/env bash
# scripts/build-image.sh — build the Docker image
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

IMAGE_NAME="${HARNESS_IMAGE:-harness:latest}"

echo "Building Docker image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" -f docker/Dockerfile .

echo "Done: $IMAGE_NAME"
```

- [ ] **Step 2: Create benchmark.sh**

```bash
#!/usr/bin/env bash
# scripts/benchmark.sh — main entry point
# Loads .env, ensures prerequisites, runs the benchmark.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Load .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Ensure polyglot-benchmark is initialized
./scripts/setup-polyglot.sh

# Ensure venv
if [ ! -d .venv ]; then
    python3.12 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
fi

# Run benchmark via Python
.venv/bin/python -m benchmark "$@"
```

- [ ] **Step 3: Create report.sh**

```bash
#!/usr/bin/env bash
# scripts/report.sh — generate report only (no benchmark run)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

if [ ! -d .venv ]; then
    python3.12 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
fi

.venv/bin/python -m benchmark --report-only "$@"
```

- [ ] **Step 4: Make all executable**

Run: `chmod +x scripts/*.sh`

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark.sh scripts/report.sh scripts/build-image.sh
git commit -m "feat: shell scripts for benchmark, report, and image build"
```

---

### Task 15: End-to-End Smoke Test

**Files:**
- No new files — verification only.

- [ ] **Step 1: Verify project structure is complete**

Run:
```bash
find . -not -path './.git/*' -not -path './.venv/*' -not -path './polyglot-benchmark/*' -not -path './node_modules/*' -type f | sort
```
Expected: all project files present.

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 3: Build Docker image**

Run: `./scripts/build-image.sh`
Expected: Image builds successfully (may take several minutes first time).

- [ ] **Step 4: Verify image contents**

Run:
```bash
docker run --rm harness:latest sh -c "which opencode && which pi && which pytest && which node && ls /app/polyglot-benchmark/python/exercises/practice/ | head -5"
```
Expected: All tools found, polyglot exercises visible.

- [ ] **Step 5: Smoke test with one exercise (requires API key)**

Run:
```bash
cp .env.example .env
# Edit .env to add your LLM_API_KEY

./scripts/benchmark.sh \
  --harnesses pi \
  --languages python \
  --repetitions 1 \
  --skip-existing
```
Expected: Container runs, metrics.json emitted, result stored in SQLite.

- [ ] **Step 6: Generate and view report**

Run: `./scripts/report.sh`
Expected: `docs/index.html` updated. Open in browser to verify leaderboard.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: end-to-end smoke test verified"
git push
```

---

## Post-Implementation Checklist

- [ ] Dockerfile builds without errors
- [ ] All pytest tests pass
- [ ] Container can invoke both opencode and pi
- [ ] Metrics extracted correctly from both harness event formats
- [ ] SQLite store UPSERT is idempotent
- [ ] `--skip-existing` skips already-completed runs
- [ ] Leaderboard HTML renders with model/language filters
- [ ] `docs/index.html` auto-committed and pushed after runs
- [ ] GitHub Pages displays the leaderboard
- [ ] `--model-url` flag overrides endpoint correctly
- [ ] New harness can be added via `harnesses/<name>/` without orchestrator changes
