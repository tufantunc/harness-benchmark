import type { TaskRun, HarnessSummary } from './types';

export function aggregate(runs: TaskRun[]): HarnessSummary[] {
  const byHarness = new Map<string, TaskRun[]>();
  for (const r of runs) {
    if (!byHarness.has(r.harness)) byHarness.set(r.harness, []);
    byHarness.get(r.harness)!.push(r);
  }

  const summaries: HarnessSummary[] = [];
  for (const [harness, items] of byHarness) {
    const total = items.length;
    const succ = items.filter(i => i.success);
    const byEx = new Map<string, boolean>();
    for (const i of items) {
      const k = `${i.language}/${i.exercise}`;
      if (!byEx.has(k)) byEx.set(k, false);
      if (i.success) byEx.set(k, true);
    }
    const passK = Array.from(byEx.values()).filter(Boolean).length / byEx.size;
    const avg = (f: number) => f / total;
    const hasTools = items.some(i => i.tool_calls > 0);
    summaries.push({
      harness,
      total_tasks: total,
      success_count: succ.length,
      success_rate: succ.length / total,
      pass_at_k: passK,
      avg_tokens_in: avg(items.reduce((s, i) => s + (i.tokens_input || 0), 0)),
      avg_tokens_out: avg(items.reduce((s, i) => s + (i.tokens_output || 0), 0)),
      avg_llm_calls: avg(items.reduce((s, i) => s + (i.llm_calls || 0), 0)),
      avg_tool_calls: hasTools ? avg(items.reduce((s, i) => s + (i.tool_calls || 0), 0)) : null,
      avg_duration: avg(items.reduce((s, i) => s + (i.duration_sec || 0), 0)),
      avg_system_prompt: avg(items.reduce((s, i) => s + (i.system_prompt_tokens || 0), 0)),
      avg_tool_schemas: avg(items.reduce((s, i) => s + (i.tool_schema_tokens || 0), 0)),
      avg_requests: avg(items.reduce((s, i) => s + (i.request_count || 0), 0)),
      prefix_stable_rate: items.filter(i => i.prefix_stable).length / total,
    });
  }
  return summaries.sort((a, b) => b.success_rate - a.success_rate);
}
