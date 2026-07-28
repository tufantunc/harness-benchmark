import { Download, ExternalLink } from 'lucide-react';

interface HeaderProps {
  model: string;
  language: string;
  onModelChange: (v: string) => void;
  onLanguageChange: (v: string) => void;
  models: string[];
  onExport: () => void;
}

export function Header({ model, language, onModelChange, onLanguageChange, models, onExport }: HeaderProps) {
  return (
    <header className="border-b border-zinc-800 pb-6 mb-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Harness Benchmark</h1>
          <p className="text-zinc-500 mt-1">Coding Agent Harness Comparison</p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/tufantunc/harness-benchmark"
            target="_blank"
            rel="noopener"
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-zinc-800 hover:border-zinc-700 transition-colors text-sm text-zinc-400"
          >
            <ExternalLink size={16} /> Repository
          </a>
          <button
            onClick={onExport}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors text-sm text-white"
          >
            <Download size={16} /> Export JSON
          </button>
        </div>
      </div>
      <div className="flex gap-3 mt-4">
        <select
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-300"
        >
          {models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          value={language}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-300"
        >
          <option value="">All Languages</option>
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
        </select>
      </div>
    </header>
  );
}
