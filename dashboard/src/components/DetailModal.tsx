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
  const maxTokens = Math.max(...summaries.map(s => s.avg_tokens_in));
  const maxDuration = Math.max(...summaries.map(s => s.avg_duration));
  const maxSchemas = Math.max(...summaries.map(s => s.avg_tool_schemas));

  const radarData = useMemo(() => {
    if (!selected) return [];
    return [
      { metric: 'Success', harness: Math.round(selected.success_rate * 100), avg: 50 },
      { metric: 'pass@k', harness: Math.round(selected.pass_at_k * 100), avg: 50 },
      { metric: 'Efficiency', harness: Math.round((1 - Math.min(1, selected.avg_tokens_in / maxTokens)) * 100), avg: 50 },
      { metric: 'Speed', harness: Math.round((1 - Math.min(1, selected.avg_duration / maxDuration)) * 100), avg: 50 },
      { metric: 'Stability', harness: Math.round(selected.prefix_stable_rate * 100), avg: 50 },
      { metric: 'Lean Tools', harness: Math.round((1 - Math.min(1, selected.avg_tool_schemas / maxSchemas)) * 100), avg: 50 },
    ];
  }, [selected, maxTokens, maxDuration, maxSchemas]);

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
