import { useMemo, useState } from 'react';
import { ArrowUpDown, Search } from 'lucide-react';
import type { HarnessSummary } from '../lib/types';
import { pct, fmt, secs, scoreBadge } from '../lib/format';

interface LeaderboardTableProps {
  summaries: HarnessSummary[];
  onSelectHarness: (harness: string) => void;
}

type SortKey = keyof HarnessSummary;

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

  const Th = ({ label, sortKey: k, className = '' }: { label: string; sortKey?: SortKey; className?: string }) => (
    <th
      className={`px-3 py-2 text-left text-xs font-medium text-zinc-500 uppercase cursor-pointer hover:text-zinc-300 ${className}`}
      onClick={() => k && toggleSort(k)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {k && <ArrowUpDown size={12} className={sortKey === k ? 'text-blue-400' : 'text-zinc-700'} />}
      </span>
    </th>
  );

  const Td = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
    <td className={`px-3 py-2 text-sm ${className}`}>{children}</td>
  );

  const columns = [
    { key: 'success_rate' as SortKey, label: 'Success', fmt: (s: HarnessSummary) => (
      <span className={`inline-flex px-2 py-0.5 rounded text-xs border ${scoreBadge(s.success_rate)}`}>{pct(s.success_rate)}</span>
    )},
    { key: 'pass_at_k' as SortKey, label: 'pass@k', fmt: (s: HarnessSummary) => pct(s.pass_at_k) },
    { key: 'avg_tokens_in' as SortKey, label: 'Tokens In', fmt: (s: HarnessSummary) => fmt(s.avg_tokens_in) },
    { key: 'avg_tokens_out' as SortKey, label: 'Tokens Out', fmt: (s: HarnessSummary) => fmt(s.avg_tokens_out) },
    { key: 'avg_llm_calls' as SortKey, label: 'LLM', fmt: (s: HarnessSummary) => s.avg_llm_calls.toFixed(1) },
    { key: 'avg_tool_calls' as SortKey, label: 'Tools', fmt: (s: HarnessSummary) => s.avg_tool_calls !== null ? s.avg_tool_calls.toFixed(1) : '—' },
    { key: 'avg_duration' as SortKey, label: 'Time', fmt: (s: HarnessSummary) => secs(s.avg_duration) },
    { key: 'avg_system_prompt' as SortKey, label: 'Sys Tok', fmt: (s: HarnessSummary) => fmt(s.avg_system_prompt) },
    { key: 'avg_tool_schemas' as SortKey, label: 'Schema', fmt: (s: HarnessSummary) => fmt(s.avg_tool_schemas) },
    { key: 'prefix_stable_rate' as SortKey, label: 'Stable', fmt: (s: HarnessSummary) => (
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
              <Th label="#" />
              <Th label="Harness" />
              {columns.map(c => <Th key={c.label} label={c.label} sortKey={c.key} />)}
            </tr>
          </thead>
          <tbody>
            {sorted.map((s, i) => (
              <tr
                key={s.harness}
                onClick={() => onSelectHarness(s.harness)}
                className={`border-t border-zinc-800 hover:bg-zinc-900 cursor-pointer ${i === 0 ? 'font-semibold' : ''}`}
              >
                <Td className="text-zinc-600">{i + 1}</Td>
                <Td className="font-medium">{s.harness}</Td>
                {columns.map(c => <Td key={c.label}>{c.fmt(s)}</Td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
