import { useState, useMemo } from 'react';
import rawData from './data/benchmark-data.json';
import type { BenchmarkData } from './lib/types';
import { Header } from './components/Header';
import { HeroCards } from './components/HeroCards';
import { TradeoffChart } from './components/TradeoffChart';
import { ExerciseHeatmap } from './components/ExerciseHeatmap';
import { LeaderboardTable } from './components/LeaderboardTable';
import { DetailModal } from './components/DetailModal';
import { Methodology } from './components/Methodology';
import { aggregate } from './lib/aggregate';

const data = rawData as BenchmarkData;

export default function App() {
  const [model, setModel] = useState('');
  const [language, setLanguage] = useState('');
  const [selectedHarness, setSelectedHarness] = useState<string | null>(null);

  const models = useMemo(() => [...new Set(data.runs.map(r => r.model))], []);
  const languages = useMemo(() => [...new Set(data.runs.map(r => r.language))], []);

  const filteredRuns = useMemo(() => {
    return data.runs.filter(r =>
      (!model || r.model === model) &&
      (!language || r.language === language)
    );
  }, [model, language]);

  const summaries = useMemo(() => aggregate(filteredRuns), [filteredRuns]);

  const handleExport = () => {
    const blob = new Blob([JSON.stringify({ ...data, runs: filteredRuns }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'benchmark-data.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto">
      <Header
        model={model}
        language={language}
        onModelChange={setModel}
        onLanguageChange={setLanguage}
        models={models}
        languages={languages}
        onExport={handleExport}
      />

      <HeroCards summaries={summaries} totalRuns={filteredRuns.length} />

      <TradeoffChart summaries={summaries} />

      <LeaderboardTable summaries={summaries} onSelectHarness={setSelectedHarness} />

      <ExerciseHeatmap runs={filteredRuns} />

      <Methodology />

      <DetailModal
        harness={selectedHarness}
        summaries={summaries}
        onClose={() => setSelectedHarness(null)}
      />

      <footer className="mt-8 pt-4 border-t border-zinc-800 text-center text-xs text-zinc-600">
        Generated at {new Date(data.generated_at).toLocaleString()} · {filteredRuns.length} runs · {summaries.length} harnesses
      </footer>
    </div>
  );
}
