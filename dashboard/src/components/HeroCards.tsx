import { Trophy, Zap, Target, BarChart3 } from 'lucide-react';
import type { HarnessSummary } from '../lib/types';
import { pct, fmt } from '../lib/format';

interface HeroCardsProps {
  summaries: HarnessSummary[];
  totalRuns: number;
}

export function HeroCards({ summaries, totalRuns }: HeroCardsProps) {
  if (!summaries.length) return null;

  const topPerformer = [...summaries].sort((a, b) => b.success_rate - a.success_rate)[0];
  const mostEfficient = [...summaries]
    .filter(s => s.success_count > 0)
    .sort((a, b) => a.avg_tokens_in - b.avg_tokens_in)[0];
  const mostReliable = [...summaries].sort((a, b) => b.pass_at_k - a.pass_at_k)[0];

  const cards = [
    { icon: Trophy, label: 'Top Performer', value: topPerformer?.harness || '-', sub: pct(topPerformer?.success_rate || 0), color: 'text-yellow-400' },
    { icon: Zap, label: 'Most Efficient', value: mostEfficient?.harness || '-', sub: `${fmt(mostEfficient?.avg_tokens_in || 0)} tok/task`, color: 'text-blue-400' },
    { icon: Target, label: 'Most Reliable', value: mostReliable?.harness || '-', sub: `pass@k ${pct(mostReliable?.pass_at_k || 0)}`, color: 'text-green-400' },
    { icon: BarChart3, label: 'Total Runs', value: fmt(totalRuns), sub: `${summaries.length} harnesses`, color: 'text-zinc-400' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {cards.map((c) => (
        <div key={c.label} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <c.icon size={16} className={c.color} />
            <span className="text-xs text-zinc-500 uppercase tracking-wide">{c.label}</span>
          </div>
          <div className="text-xl font-bold">{c.value}</div>
          <div className={`text-sm ${c.color}`}>{c.sub}</div>
        </div>
      ))}
    </div>
  );
}
