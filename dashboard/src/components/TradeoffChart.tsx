import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import type { HarnessSummary } from '../lib/types';
import { fmt, pct } from '../lib/format';

interface TradeoffChartProps {
  summaries: HarnessSummary[];
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ payload: HarnessSummary }>;
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs">
      <div className="font-bold mb-1">{d.harness}</div>
      <div className="text-zinc-400">Success: {pct(d.success_rate)}</div>
      <div className="text-zinc-400">Tokens: {fmt(d.avg_tokens_in)}</div>
      <div className="text-zinc-400">Schema: {fmt(d.avg_tool_schemas)} tok</div>
    </div>
  );
}

export function TradeoffChart({ summaries }: TradeoffChartProps) {
  const data = summaries.map(s => ({
    ...s,
    x: s.avg_tokens_in,
    y: s.success_rate * 100,
    z: s.avg_tool_schemas,
    name: s.harness,
  }));

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 mb-8">
      <h2 className="text-lg font-semibold mb-4">Token Efficiency vs Success Rate</h2>
      <ResponsiveContainer width="100%" height={350}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            type="number"
            dataKey="x"
            name="Tokens"
            stroke="#52525b"
            tick={{ fill: '#71717a', fontSize: 11 }}
            tickFormatter={(v) => fmt(v)}
            label={{ value: 'Avg Tokens / Task', position: 'bottom', fill: '#71717a', fontSize: 12, offset: 10 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Success"
            stroke="#52525b"
            tick={{ fill: '#71717a', fontSize: 11 }}
            tickFormatter={(v) => `${v}%`}
            domain={[0, 100]}
            label={{ value: 'Success Rate', angle: -90, position: 'insideLeft', fill: '#71717a', fontSize: 12 }}
          />
          <ZAxis type="number" dataKey="z" range={[60, 400]} />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#52525b' }} />
          <Scatter data={data} fill="#3b82f6">
            <LabelList dataKey="name" position="top" fill="#a1a1aa" fontSize={11} />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
