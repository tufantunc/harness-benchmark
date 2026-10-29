#!/usr/bin/env python3
"""Backfill cache_read_tokens / tokens_cached for stored runs.

The proxy used to ignore OpenAI Chat `prompt_tokens_details.cached_tokens`,
so OpenAI-protocol runs stored cache_read_tokens = 0 and tokens_cached only
when the harness's own events reported it. This recomputes both from the
captured responses, with the same rule as docker/entrypoint.sh
(tokens_cached = proxy cache_read or parsed tokens_cached).

Dry run by default (prints before/after per harness); --apply writes.
Usage: backfill-openai-cache.py [--results results] [--apply]
"""
import argparse
import json
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "recompute-cache-read.js"


def parsed_cached(results: Path, artifact_path: str) -> int:
    try:
        return json.loads((results / artifact_path / "parsed-metrics.json").read_text()).get("tokens_cached", 0)
    except (OSError, ValueError):
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results", type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    out = subprocess.run(["node", str(SCRIPT), str(args.results)], capture_output=True, text=True, check=True)
    recomputed = {r["artifact_path"]: r for r in map(json.loads, out.stdout.splitlines())}

    conn = sqlite3.connect(args.results / "store.db")
    rows = conn.execute(
        "SELECT id, harness, artifact_path, tokens_cached, cache_read_tokens, request_count FROM runs"
    ).fetchall()

    stats = defaultdict(lambda: defaultdict(int))
    updates, decreased = [], []
    for run_id, harness, artifact_path, cached, cache_read, request_count in rows:
        s = stats[harness]
        s["rows"] += 1
        s["cached_before"] += cached
        s["cache_read_before"] += cache_read
        r = recomputed.get(artifact_path)
        # Skip when nothing was captured, or when the artifact directory holds
        # a different run than the stored row (its request_count disagrees).
        if not r or not r["responses"] or r["request_count"] != request_count:
            s["skipped"] += 1
            new_cache_read, new_cached = cache_read, cached
        else:
            new_cache_read = r["cache_read_tokens"]
            new_cached = new_cache_read or parsed_cached(args.results, artifact_path)
        if new_cache_read < cache_read or new_cached < cached:
            decreased.append((harness, artifact_path, cached, new_cached, cache_read, new_cache_read))
        if (new_cached, new_cache_read) != (cached, cache_read):
            s["changed"] += 1
            updates.append((new_cached, new_cache_read, run_id))
        s["cached_after"] += new_cached
        s["cache_read_after"] += new_cache_read

    cols = ["rows", "skipped", "changed", "cached_before", "cached_after", "cache_read_before", "cache_read_after"]
    print("harness".ljust(12) + "".join(c.rjust(18) for c in cols))
    for h in sorted(stats):
        print(h.ljust(12) + "".join(f"{stats[h][c]:,}".rjust(18) for c in cols))
    print(f"\n{len(updates)} of {len(rows)} rows would change; {len(decreased)} would decrease")
    for d in decreased[:20]:
        print("  decrease:", d)

    if not args.apply:
        print("dry run — pass --apply to write")
        return 0
    if decreased:
        print("refusing to apply: some values would decrease", file=sys.stderr)
        return 1
    with conn:
        conn.executemany("UPDATE runs SET tokens_cached = ?, cache_read_tokens = ? WHERE id = ?", updates)
    print(f"updated {len(updates)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
