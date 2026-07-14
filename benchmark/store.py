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
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    system_prompt_tokens: int = 0
    tool_schema_tokens: int = 0
    prefix_stable: bool = True
    request_count: int = 0


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

MIGRATIONS = {
    "cache_write_tokens": "INTEGER NOT NULL DEFAULT 0",
    "cache_read_tokens": "INTEGER NOT NULL DEFAULT 0",
    "system_prompt_tokens": "INTEGER NOT NULL DEFAULT 0",
    "tool_schema_tokens": "INTEGER NOT NULL DEFAULT 0",
    "prefix_stable": "BOOLEAN NOT NULL DEFAULT 1",
    "request_count": "INTEGER NOT NULL DEFAULT 0",
}


class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)
            existing = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
            for col, decl in MIGRATIONS.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {decl}")

    def upsert(self, result: RunResult):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, harness, model, language, exercise, repetition,
                    success, tokens_input, tokens_output, tokens_cached, cost_usd,
                    duration_sec, tool_calls, llm_calls, diff_loc, timed_out, tampered,
                    artifact_path, cache_write_tokens, cache_read_tokens,
                    system_prompt_tokens, tool_schema_tokens, prefix_stable, request_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    cache_write_tokens=excluded.cache_write_tokens,
                    cache_read_tokens=excluded.cache_read_tokens,
                    system_prompt_tokens=excluded.system_prompt_tokens,
                    tool_schema_tokens=excluded.tool_schema_tokens,
                    prefix_stable=excluded.prefix_stable,
                    request_count=excluded.request_count,
                    created_at=CURRENT_TIMESTAMP
                """,
                (
                    result.run_id, result.harness, result.model, result.language,
                    result.exercise, result.repetition, result.success,
                    result.tokens_input, result.tokens_output, result.tokens_cached,
                    result.cost_usd, result.duration_sec, result.tool_calls,
                    result.llm_calls, result.diff_loc, result.timed_out,
                    result.tampered, result.artifact_path,
                    result.cache_write_tokens, result.cache_read_tokens,
                    result.system_prompt_tokens, result.tool_schema_tokens,
                    result.prefix_stable, result.request_count,
                ),
            )

    def exists(self, harness: str, model: str, language: str, exercise: str, rep: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM runs WHERE harness=? AND model=? AND language=? AND exercise=? AND repetition=?",
                (harness, model, language, exercise, rep),
            ).fetchone()
            return row is not None

    def exists_successful(self, harness: str, model: str, language: str, exercise: str, rep: int) -> bool:
        """True only if the task exists AND succeeded."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT success FROM runs WHERE harness=? AND model=? AND language=? AND exercise=? AND repetition=?",
                (harness, model, language, exercise, rep),
            ).fetchone()
            return row is not None and bool(row[0])

    def count_by_success(self, harness: str | None = None, model: str | None = None) -> dict[str, int]:
        clauses = []
        params = []
        if harness:
            clauses.append("harness = ?")
            params.append(harness)
        if model:
            clauses.append("model = ?")
            params.append(model)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT success, COUNT(*) FROM runs{where} GROUP BY success",
                params,
            ).fetchall()
        return {"success": sum(c for s, c in rows if s), "failed": sum(c for s, c in rows if not s)}

    def _row_to_result(self, r: sqlite3.Row) -> RunResult:
        return RunResult(
            run_id=r["run_id"], harness=r["harness"], model=r["model"],
            language=r["language"], exercise=r["exercise"],
            repetition=r["repetition"], success=bool(r["success"]),
            tokens_input=r["tokens_input"], tokens_output=r["tokens_output"],
            tokens_cached=r["tokens_cached"], cost_usd=r["cost_usd"],
            duration_sec=r["duration_sec"], tool_calls=r["tool_calls"],
            llm_calls=r["llm_calls"], diff_loc=r["diff_loc"],
            timed_out=bool(r["timed_out"]), tampered=bool(r["tampered"]),
            artifact_path=r["artifact_path"],
            cache_write_tokens=r["cache_write_tokens"] if "cache_write_tokens" in r.keys() else 0,
            cache_read_tokens=r["cache_read_tokens"] if "cache_read_tokens" in r.keys() else 0,
            system_prompt_tokens=r["system_prompt_tokens"] if "system_prompt_tokens" in r.keys() else 0,
            tool_schema_tokens=r["tool_schema_tokens"] if "tool_schema_tokens" in r.keys() else 0,
            prefix_stable=bool(r["prefix_stable"]) if "prefix_stable" in r.keys() else True,
            request_count=r["request_count"] if "request_count" in r.keys() else 0,
        )

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

        return [self._row_to_result(r) for r in rows]

    def export_json(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM runs ORDER BY harness, model, language, exercise").fetchall()
        return [dict(r) for r in rows]
