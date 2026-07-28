import { useMemo } from 'react';
import type { TaskRun } from '../lib/types';

interface ExerciseHeatmapProps {
  runs: TaskRun[];
}

export function ExerciseHeatmap({ runs }: ExerciseHeatmapProps) {
  const { exercises, harnesses, matrix } = useMemo(() => {
    const harnessSet = [...new Set(runs.map(r => r.harness))].sort();
    const exerciseSet = [...new Set(runs.map(r => `${r.language}/${r.exercise}`))].sort();

    const grid = new Map<string, Map<string, { pass: number; total: number }>>();
    for (const r of runs) {
      const ex = `${r.language}/${r.exercise}`;
      if (!grid.has(ex)) grid.set(ex, new Map());
      const h = grid.get(ex)!;
      if (!h.has(r.harness)) h.set(r.harness, { pass: 0, total: 0 });
      const cell = h.get(r.harness)!;
      cell.total++;
      if (r.success) cell.pass++;
    }

    const exDifficulty = exerciseSet.map(ex => {
      let totalPass = 0, totalAll = 0;
      for (const h of harnessSet) {
        const cell = grid.get(ex)?.get(h);
        if (cell) { totalPass += cell.pass; totalAll += cell.total; }
      }
      return { ex, rate: totalAll ? totalPass / totalAll : 0 };
    }).sort((a, b) => a.rate - b.rate);

    return { exercises: exDifficulty.map(e => e.ex), harnesses: harnessSet, matrix: grid };
  }, [runs]);

  function cellColor(ex: string, harness: string): string {
    const cell = matrix.get(ex)?.get(harness);
    if (!cell) return 'bg-zinc-900';
    const rate = cell.pass / cell.total;
    if (rate === 1) return 'bg-green-600';
    if (rate >= 1/3) return 'bg-yellow-600';
    if (rate > 0) return 'bg-orange-700';
    return 'bg-red-700';
  }

  function cellText(ex: string, harness: string): string {
    const cell = matrix.get(ex)?.get(harness);
    if (!cell) return '—';
    return `${cell.pass}/${cell.total}`;
  }

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 mb-8">
      <h2 className="text-lg font-semibold mb-4">Exercise × Harness</h2>
      <div className="overflow-x-auto">
        <table className="text-xs">
          <thead>
            <tr>
              <th className="px-2 py-1 text-left text-zinc-500 sticky left-0 bg-zinc-900/80">Exercise</th>
              {harnesses.map(h => (
                <th key={h} className="px-2 py-1 text-center text-zinc-500 min-w-[60px]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {exercises.map(ex => (
              <tr key={ex} className="border-t border-zinc-800/50">
                <td className="px-2 py-1 text-zinc-400 sticky left-0 bg-zinc-900/80 whitespace-nowrap">{ex}</td>
                {harnesses.map(h => (
                  <td
                    key={h}
                    className={`px-2 py-1 text-center text-white/80 ${cellColor(ex, h)}`}
                    title={`${ex} × ${h}: ${cellText(ex, h)}`}
                  >
                    {cellText(ex, h)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
