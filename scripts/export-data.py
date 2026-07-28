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

    data = {"runs": runs, "generated_at": datetime.now().isoformat()}

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2))
    print(f"Exported {len(runs)} runs to {output}")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "results/store.db"
    out = sys.argv[2] if len(sys.argv) > 2 else "dashboard/src/data/benchmark-data.json"
    export(db, out)
