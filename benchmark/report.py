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

        by_exercise: dict[tuple, list[bool]] = defaultdict(list)
        for r in results:
            by_exercise[(r.language, r.exercise)].append(r.success)
        pass_at_k = sum(1 for ex, vals in by_exercise.items() if any(vals)) / len(by_exercise) if by_exercise else 0.0

        costs = [r.cost_usd for r in successes] if successes else [0.0]
        tokens = [r.tokens_input + r.tokens_output for r in successes] if successes else [0]
        durations = [r.duration_sec for r in results] if results else [0.0]
        tool_calls = [r.tool_calls for r in results] if results else [0]
        cache_writes = [r.cache_write_tokens for r in results] if results else [0]
        cache_reads = [r.cache_read_tokens for r in results] if results else [0]
        sys_prompt = [r.system_prompt_tokens for r in results] if results else [0]
        tool_schemas = [r.tool_schema_tokens for r in results] if results else [0]
        requests = [r.request_count for r in results] if results else [0]
        stable_count = sum(1 for r in results if r.prefix_stable)

        entries.append({
            "harness": harness,
            "total_tasks": total,
            "success_rate": round(success_rate, 4),
            "pass_at_k": round(pass_at_k, 4),
            "avg_cost_per_task": round(statistics.mean(costs), 4) if costs else 0.0,
            "tokens_per_success": round(statistics.mean(tokens)) if tokens else 0,
            "avg_duration": round(statistics.mean(durations), 1) if durations else 0.0,
            "avg_tool_calls": round(statistics.mean(tool_calls), 1) if tool_calls else 0.0,
            "avg_cache_write": round(statistics.mean(cache_writes)) if cache_writes else 0,
            "avg_cache_read": round(statistics.mean(cache_reads)) if cache_reads else 0,
            "avg_sys_prompt_tokens": round(statistics.mean(sys_prompt)) if sys_prompt else 0,
            "avg_tool_schema_tokens": round(statistics.mean(tool_schemas)) if tool_schemas else 0,
            "prefix_stable_rate": round(stable_count / total, 4) if total > 0 else 0.0,
            "avg_requests": round(statistics.mean(requests), 1) if requests else 0,
        })

    entries.sort(key=lambda e: (
        -e["success_rate"],
        e["tokens_per_success"],
        e["avg_cost_per_task"],
        e["avg_duration"],
    ))

    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return entries


def generate_markdown(leaderboard: list[dict], model: str) -> str:
    lines = [
        f"# Leaderboard — {model}",
        "",
        "## Summary",
        "",
        "| Rank | Harness | Tasks | Success | pass@k | Tokens/Success | Cost/Task | Avg Time | Avg Requests |",
        "|------|---------|-------|---------|--------|----------------|-----------|----------|--------------|",
    ]
    for e in leaderboard:
        lines.append(
            f"| {e['rank']} | {e['harness']} | {e['total_tasks']} | "
            f"{e['success_rate']:.1%} | {e['pass_at_k']:.1%} | "
            f"{e['tokens_per_success']:,} | ${e['avg_cost_per_task']:.4f} | "
            f"{e['avg_duration']:.0f}s | {e['avg_requests']:.1f} |"
        )

    lines.extend([
        "",
        "## Cache & Overhead",
        "",
        "| Harness | Cache Write | Cache Read | Sys Prompt | Tool Schemas | Prefix Stable |",
        "|---------|-------------|------------|------------|--------------|---------------|",
    ])
    for e in leaderboard:
        lines.append(
            f"| {e['harness']} | "
            f"{e['avg_cache_write']:,} | {e['avg_cache_read']:,} | "
            f"{e['avg_sys_prompt_tokens']:,} | {e['avg_tool_schema_tokens']:,} | "
            f"{e['prefix_stable_rate']:.0%} |"
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

const models = [...new Set(DATA.map(e => e.model))];
models.forEach(m => {{
  const opt = document.createElement('option');
  opt.value = m; opt.textContent = m;
  document.getElementById('model-select').appendChild(opt);
}});

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

    assets_dir = pages_path / "assets"
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "leaderboard-data.json").write_text(json.dumps(raw_data, indent=2))

    html = HTML_TEMPLATE.format(data=json.dumps(raw_data))
    (pages_path / "index.html").write_text(html)

    if raw_data:
        models = sorted(set(r["model"] for r in raw_data))
        md_parts = []
        for model in models:
            lb = compute_leaderboard(store, model=model)
            md_parts.append(generate_markdown(lb, model))
        (pages_path / "leaderboard.md").write_text("\n\n---\n\n".join(md_parts))

    print(f"Report generated in {pages_path}/")

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
