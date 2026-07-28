import { useMemo } from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend } from 'recharts';
import { X } from 'lucide-react';
import type { HarnessSummary } from '../lib/types';
import { pct, fmt, secs } from '../lib/format';

interface DetailModalProps {
  harness: string | null;
  summaries: HarnessSummary[];
  onClose: () => void;
}

export function DetailModal({ harness, summaries, onClose }: DetailModalProps) {
  const selected = summaries.find(s => s.harness === harness);

  const radarData = useMemo(() => {
    if (!selected || summaries.length === 0) return [];
    const maxTokens = Math.max(...summaries.map(s => s.avg_tokens_in)) || 1;
    const maxDuration = Math.max(...summaries.map(s => s.avg_duration)) || 1;
    const maxSchemas = Math.max(...summaries.map(s => s.avg_tool_schemas)) || 1;

    // Compute real peer averages
    const n = summaries.length;
    const peerAvg = (sel: (s: HarnessSummary) => number) => summaries.reduce((a, s) => a + sel(s), 0) / n;

    const metrics = [
      { metric: 'Success', val: selected.success_rate, peer: peerAvg(s => s.success_rate), max: 1 },
      { metric: 'pass@k', val: selected.pass_at_k, peer: peerAvg(s => s.pass_at_k), max: 1 },
      { metric: 'Efficiency', val: 1 - Math.min(1, selected.avg_tokens_in / maxTokens), peer: 1 - peerAvg(s => Math.min(1, s.avg_tokens_in / maxTokens)), max: 1 },
      { metric: 'Speed', val: 1 - Math.min(1, selected.avg_duration / maxDuration), peer: 1 - peerAvg(s => Math.min(1, s.avg_duration / maxDuration)), max: 1 },
      { metric: 'Stability', val: selected.prefix_stable_rate, peer: peerAvg(s => s.prefix_stable_rate), max: 1 },
      { metric: 'Lean Tools', val: 1 - Math.min(1, selected.avg_tool_schemas / maxSchemas), peer: 1 - peerAvg(s => Math.min(1, s.avg_tool_schemas / maxSchemas)), max: 1 },
    ];

    return metrics.map(m => ({
      metric: m.metric,
      harness: Math.round(m.val * 100),
      'peer avg': Math.round(m.peer * 100),
    }));
  }, [selected, summaries]);

  if (!harness || !selected) return null;

  const metrics = [
    { label: 'Success Rate', value: pct(selected.success_rate) },
    { label: 'pass@k', value: pct(selected.pass_at_k) },
    { label: 'Avg Tokens In', value: fmt(selected.avg_tokens_in) },
    { label: 'Avg Tokens Out', value: fmt(selected.avg_tokens_out) },
    { label: 'LLM Calls/Task', value: selected.avg_llm_calls.toFixed(1) },
    { label: 'Tool Calls/Task', value: selected.avg_tool_calls !== null ? selected.avg_tool_calls.toFixed(1) : '—' },
    { label: 'Avg Duration', value: secs(selected.avg_duration) },
    { label: 'System Prompt', value: fmt(selected.avg_system_prompt) + ' tok' },
    { label: 'Tool Schemas', value: fmt(selected.avg_tool_schemas) + ' tok' },
    { label: 'Prefix Stable', value: pct(selected.prefix_stable_rate) },
  ];

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">{harness}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X size={20} />
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#27272a" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#71717a', fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#52525b', fontSize: 9 }} stroke="#27272a" />
                <Radar name="Harness" dataKey="harness" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                <Radar name="Peer Avg" dataKey="peer avg" stroke="#71717a" fill="#71717a" fillOpacity={0.1} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-2">
            {metrics.map(m => (
              <div key={m.label} className="flex justify-between text-sm border-b border-zinc-800/50 pb-1">
                <span className="text-zinc-500">{m.label}</span>
                <span className="font-medium">{m.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
