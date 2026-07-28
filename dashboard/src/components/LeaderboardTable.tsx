import { useMemo, useState } from 'react';
import { ArrowUpDown, Search } from 'lucide-react';
import type { HarnessSummary } from '../lib/types';
import { pct, fmt, secs, scoreBadge } from '../lib/format';

interface LeaderboardTableProps {
  summaries: HarnessSummary[];
  onSelectHarness: (harness: string) => void;
}

type SortKey = 'success_rate' | 'pass_at_k' | 'avg_tokens_in' | 'avg_tokens_out' | 'avg_llm_calls' | 'avg_tool_calls' | 'avg_duration' | 'avg_system_prompt' | 'avg_tool_schemas' | 'prefix_stable_rate';

// Module-scope helpers (avoid re-mounting DOM on every render)
function renderTh(label: string, sortKey: SortKey | undefined, activeKey: SortKey, toggleSort: (k: SortKey) => void) {
  return (
    <th
      className="px-3 py-2 text-left text-xs font-medium text-zinc-500 uppercase cursor-pointer hover:text-zinc-300"
      onClick={() => sortKey && toggleSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {sortKey && <ArrowUpDown size={12} className={activeKey === sortKey ? 'text-blue-400' : 'text-zinc-700'} />}
      </span>
    </th>
  );
}

export function LeaderboardTable({ summaries, onSelectHarness }: LeaderboardTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('success_rate');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [search, setSearch] = useState('');

  const sorted = useMemo(() => {
    let rows = [...summaries];
    if (search) {
      rows = rows.filter(r => r.harness.toLowerCase().includes(search.toLowerCase()));
    }
    rows.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      const cmp = (av as number) - (bv as number);
      return sortDir === 'desc' ? -cmp : cmp;
    });
    return rows;
  }, [summaries, sortKey, sortDir, search]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const columns: { key: SortKey; label: string; render: (s: HarnessSummary) => React.ReactNode }[] = [
    { key: 'success_rate', label: 'Success', render: s => (
      <span className={`inline-flex px-2 py-0.5 rounded text-xs border ${scoreBadge(s.success_rate)}`}>{pct(s.success_rate)}</span>
    )},
    { key: 'pass_at_k', label: 'pass@k', render: s => pct(s.pass_at_k) },
    { key: 'avg_tokens_in', label: 'Tokens In', render: s => fmt(s.avg_tokens_in) },
    { key: 'avg_tokens_out', label: 'Tokens Out', render: s => fmt(s.avg_tokens_out) },
    { key: 'avg_llm_calls', label: 'LLM', render: s => s.avg_llm_calls.toFixed(1) },
    { key: 'avg_tool_calls', label: 'Tools', render: s => s.avg_tool_calls !== null ? s.avg_tool_calls.toFixed(1) : '—' },
    { key: 'avg_duration', label: 'Time', render: s => secs(s.avg_duration) },
    { key: 'avg_system_prompt', label: 'Sys Tok', render: s => fmt(s.avg_system_prompt) },
    { key: 'avg_tool_schemas', label: 'Schema', render: s => fmt(s.avg_tool_schemas) },
    { key: 'prefix_stable_rate', label: 'Stable', render: s => (
      <span className={s.prefix_stable_rate > 0.8 ? 'text-green-500' : 'text-red-500'}>{pct(s.prefix_stable_rate)}</span>
    )},
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search harness..."
            className="w-full pl-9 pr-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-300"
          />
        </div>
      </div>
      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full">
          <thead className="bg-zinc-900/50">
            <tr>
              {renderTh('#', undefined, sortKey, toggleSort)}
              {renderTh('Harness', undefined, sortKey, toggleSort)}
              {columns.map(c => <th key={c.label} className="px-3 py-2 text-left text-xs font-medium text-zinc-500 uppercase cursor-pointer hover:text-zinc-300" onClick={() => toggleSort(c.key)}>
                <span className="inline-flex items-center gap-1">
                  {c.label}
                  <ArrowUpDown size={12} className={sortKey === c.key ? 'text-blue-400' : 'text-zinc-700'} />
                </span>
              </th>)}
            </tr>
          </thead>
          <tbody>
            {sorted.map((s, i) => (
              <tr
                key={s.harness}
                onClick={() => onSelectHarness(s.harness)}
                className={`border-t border-zinc-800 hover:bg-zinc-900 cursor-pointer ${i === 0 ? 'font-semibold' : ''}`}
              >
                <td className="px-3 py-2 text-sm text-zinc-600">{i + 1}</td>
                <td className="px-3 py-2 text-sm font-medium">{s.harness}</td>
                {columns.map(c => <td key={c.label} className="px-3 py-2 text-sm">{c.render(s)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
