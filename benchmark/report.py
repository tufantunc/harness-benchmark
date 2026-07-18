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
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a1a; }
  h1 { font-size: 1.6rem; }
  h2 { font-size: 1.2rem; margin-top: 2rem; }
  table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; font-size: 0.9rem; }
  th, td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; white-space: nowrap; }
  th { background: #f0f0f0; font-weight: 600; cursor: pointer; }
  th:hover { background: #e0e0e0; }
  tr:nth-child(even) { background: #fafafa; }
  .rank-1 { font-weight: bold; }
  .pass { color: #16a34a; font-weight: 600; }
  .fail { color: #dc2626; }
  .muted { color: #666; }
  .controls { margin: 1rem 0; display: flex; gap: 1rem; align-items: center; }
  select { padding: 0.3rem 0.5rem; }
  .harness-row:hover { background: #e8f0fe; cursor: pointer; }
  .detail-row { display: none; }
  .detail-row.show { display: table-row; }
  .badge { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.75rem; font-weight: 600; }
  .badge-yes { background: #dcfce7; color: #166534; }
  .badge-no { background: #fee2e2; color: #991b1b; }
  .stab { color: #2563eb; }
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

<div id="summary"></div>
<div id="cache"></div>
<div id="detail"></div>

<script>
const DATA = __DATA_PLACEHOLDER__;

function aggregate(items) {
  const total = items.length;
  const succ = items.filter(i => i.success);
  // pass@k: group by (language, exercise), any rep succeeded
  const byEx = {};
  items.forEach(i => {
    const k = i.language + '/' + i.exercise;
    if (!byEx[k]) byEx[k] = false;
    if (i.success) byEx[k] = true;
  });
  const exKeys = Object.keys(byEx);
  const passK = exKeys.length ? exKeys.filter(k => byEx[k]).length / exKeys.length : 0;
  const avg = (f) => total ? f / total : 0;
  return {
    total, passK,
    successRate: succ.length / total,
    avgIn: avg(items.reduce((s,i) => s + (i.tokens_input||0), 0)),
    avgOut: avg(items.reduce((s,i) => s + (i.tokens_output||0), 0)),
    avgCached: avg(items.reduce((s,i) => s + (i.tokens_cached||0), 0)),
    avgCost: avg(items.reduce((s,i) => s + (i.cost_usd||0), 0)),
    avgLLM: avg(items.reduce((s,i) => s + (i.llm_calls||0), 0)),
    avgTools: avg(items.reduce((s,i) => s + (i.tool_calls||0), 0)),
    avgDur: avg(items.reduce((s,i) => s + (i.duration_sec||0), 0)),
    avgCacheWrite: avg(items.reduce((s,i) => s + (i.cache_write_tokens||0), 0)),
    avgCacheRead: avg(items.reduce((s,i) => s + (i.cache_read_tokens||0), 0)),
    avgSysPrompt: avg(items.reduce((s,i) => s + (i.system_prompt_tokens||0), 0)),
    avgToolSchema: avg(items.reduce((s,i) => s + (i.tool_schema_tokens||0), 0)),
    avgRequests: avg(items.reduce((s,i) => s + (i.request_count||0), 0)),
    stableRate: items.filter(i => i.prefix_stable).length / total,
  };
}

function fmt(n) { return Math.round(n).toLocaleString(); }
function pct(n) { return (n * 100).toFixed(1) + '%'; }
function money(n) { return '$' + n.toFixed(4); }

function render(model, lang) {
  const filtered = DATA.filter(e => (!model || e.model === model) && (!lang || e.language === lang));
  const byHarness = {};
  filtered.forEach(e => {
    if (!byHarness[e.harness]) byHarness[e.harness] = [];
    byHarness[e.harness].push(e);
  });

  const entries = Object.entries(byHarness).map(([harness, items]) => ({
    harness, items, ...aggregate(items)
  }));
  entries.sort((a, b) => b.successRate - a.successRate || a.avgIn + a.avgOut - b.avgIn - b.avgOut);

  // Summary table
  let html = '<h2>Summary</h2><table><thead><tr>' +
    '<th>#</th><th>Harness</th><th>Tasks</th><th>Success</th><th>pass@k</th>' +
    '<th>Tokens In</th><th>Tokens Out</th><th>LLM Calls</th><th>Tools</th>' +
    '<th>Cost/Run</th><th>Avg Time</th></tr></thead><tbody>';
  entries.forEach((r, i) => {
    html += '<tr class="harness-row ' + (i===0?'rank-1':'') + '" onclick="toggleDetail(\\'' + r.harness + '\\')">' +
      '<td>' + (i+1) + '</td><td>' + r.harness + '</td><td>' + r.total + '</td>' +
      '<td>' + pct(r.successRate) + '</td><td>' + pct(r.passK) + '</td>' +
      '<td>' + fmt(r.avgIn) + '</td><td>' + fmt(r.avgOut) + '</td>' +
      '<td>' + r.avgLLM.toFixed(1) + '</td><td>' + r.avgTools.toFixed(1) + '</td>' +
      '<td>' + money(r.avgCost) + '</td><td>' + Math.round(r.avgDur) + 's</td></tr>';
  });
  html += '</tbody></table>';
  document.getElementById('summary').innerHTML = html;

  // Cache & Overhead table
  let cacheHtml = '<h2>Cache & Overhead</h2><table><thead><tr>' +
    '<th>Harness</th><th>Cache Write</th><th>Cache Read</th>' +
    '<th>Sys Prompt</th><th>Tool Schemas</th><th>API Reqs</th>' +
    '<th>Prefix Stable</th></tr></thead><tbody>';
  entries.forEach(r => {
    cacheHtml += '<tr><td>' + r.harness + '</td>' +
      '<td>' + fmt(r.avgCacheWrite) + '</td><td>' + fmt(r.avgCacheRead) + '</td>' +
      '<td>' + fmt(r.avgSysPrompt) + '</td><td>' + fmt(r.avgToolSchema) + '</td>' +
      '<td>' + r.avgRequests.toFixed(1) + '</td>' +
      '<td><span class="badge ' + (r.stableRate > 0.8 ? 'badge-yes' : 'badge-no') + '">' + pct(r.stableRate) + '</span></td></tr>';
  });
  cacheHtml += '</tbody></table>';
  document.getElementById('cache').innerHTML = cacheHtml;

  // Detail placeholder
  document.getElementById('detail').innerHTML = '';
}

function toggleDetail(harness) {
  const el = document.getElementById('detail');
  if (el.dataset.current === harness) {
    el.innerHTML = '';
    el.dataset.current = '';
    return;
  }
  el.dataset.current = harness;
  const model = document.getElementById('model-select').value;
  const lang = document.getElementById('lang-select').value;
  const items = DATA.filter(e => e.harness === harness && (!model || e.model === model) && (!lang || e.language === lang));

  // Group by exercise
  const byEx = {};
  items.forEach(i => {
    const k = i.language + '/' + i.exercise;
    if (!byEx[k]) byEx[k] = [];
    byEx[k].push(i);
  });

  let html = '<h2>' + harness + ' — Per Exercise</h2><table><thead><tr>' +
    '<th>Exercise</th><th>R1</th><th>R2</th><th>R3</th>' +
    '<th>Tokens In</th><th>Tokens Out</th><th>LLM</th><th>Tools</th><th>Time</th></tr></thead><tbody>';
  Object.keys(byEx).sort().forEach(k => {
    const reps = byEx[k];
    const anySucc = reps.some(r => r.success);
    const avgIn = Math.round(reps.reduce((s,r) => s + (r.tokens_input||0), 0) / reps.length);
    const avgOut = Math.round(reps.reduce((s,r) => s + (r.tokens_output||0), 0) / reps.length);
    const avgLLM = (reps.reduce((s,r) => s + (r.llm_calls||0), 0) / reps.length).toFixed(0);
    const avgTools = (reps.reduce((s,r) => s + (r.tool_calls||0), 0) / reps.length).toFixed(0);
    const avgDur = Math.round(reps.reduce((s,r) => s + r.duration_sec, 0) / reps.length);
    const cells = [1,2,3].map(n => {
      const r = reps.find(x => x.repetition === n);
      return r ? (r.success ? '<span class="pass">PASS</span>' : '<span class="fail">FAIL</span>') : '—';
    }).join('</td><td>');
    html += '<tr><td>' + k + '</td><td>' + cells + '</td>' +
      '<td>' + avgIn.toLocaleString() + '</td><td>' + avgOut.toLocaleString() + '</td>' +
      '<td>' + avgLLM + '</td><td>' + avgTools + '</td><td>' + avgDur + 's</td></tr>';
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

function filter() {
  render(document.getElementById('model-select').value, document.getElementById('lang-select').value);
}

const models = [...new Set(DATA.map(e => e.model))];
models.forEach(m => {
  const opt = document.createElement('option');
  opt.value = m; opt.textContent = m;
  document.getElementById('model-select').appendChild(opt);
});

if (models.length > 0) {
  document.getElementById('model-select').value = models[0];
  render(models[0], '');
} else {
  render('', '');
}
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

    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json.dumps(raw_data))
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
