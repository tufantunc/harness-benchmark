#!/usr/bin/env python3
"""Export SQLite benchmark results to JSON for the dashboard."""
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def export(db_path: str = "results/store.db", output: str = "dashboard/src/data/benchmark-data.json"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT * FROM runs ORDER BY harness, language, exercise, repetition").fetchall()
    runs = [dict(r) for r in rows]

    by_harness = defaultdict(list)
    for r in runs:
        by_harness[r["harness"]].append(r)

    summaries = []
    for harness, items in sorted(by_harness.items()):
        total = len(items)
        succ = [i for i in items if i["success"]]
        by_ex = {}
        for i in items:
            k = (i["language"], i["exercise"])
            if k not in by_ex:
                by_ex[k] = False
            if i["success"]:
                by_ex[k] = True
        pass_k = sum(1 for v in by_ex.values() if v) / len(by_ex) if by_ex else 0
        avg = lambda f: f / total if total else 0
        summaries.append({
            "harness": harness,
            "total_tasks": total,
            "success_count": len(succ),
            "success_rate": len(succ) / total if total else 0,
            "pass_at_k": pass_k,
            "avg_tokens_in": avg(sum(i["tokens_input"] or 0 for i in items)),
            "avg_tokens_out": avg(sum(i["tokens_output"] or 0 for i in items)),
            "avg_llm_calls": avg(sum(i["llm_calls"] or 0 for i in items)),
            "avg_tool_calls": avg(sum(i["tool_calls"] or 0 for i in items)) if any(i["tool_calls"] for i in items) else None,
            "avg_duration": avg(sum(i["duration_sec"] or 0 for i in items)),
            "avg_system_prompt": avg(sum(i["system_prompt_tokens"] or 0 for i in items)),
            "avg_tool_schemas": avg(sum(i["tool_schema_tokens"] or 0 for i in items)),
            "avg_requests": avg(sum(i["request_count"] or 0 for i in items)),
            "prefix_stable_rate": sum(1 for i in items if i["prefix_stable"]) / total if total else 0,
        })

    data = {"runs": runs, "summaries": summaries, "generated_at": datetime.now().isoformat()}

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2))
    print(f"Exported {len(runs)} runs, {len(summaries)} harnesses to {output}")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "results/store.db"
    out = sys.argv[2] if len(sys.argv) > 2 else "dashboard/src/data/benchmark-data.json"
    export(db, out)
