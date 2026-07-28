import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

function AccordionItem({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-zinc-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full py-3 text-left text-sm font-medium text-zinc-300 hover:text-zinc-100"
      >
        {title}
        <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''} text-zinc-600`} />
      </button>
      {open && <div className="pb-4 text-sm text-zinc-500 leading-relaxed">{children}</div>}
    </div>
  );
}

export function Methodology() {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 mt-8">
      <h2 className="text-lg font-semibold mb-2">Methodology & FAQ</h2>
      <AccordionItem title="How does the benchmark work?">
        Each harness runs identical coding exercises (Aider Polyglot Benchmark — Exercism practice problems)
        in isolated Docker containers, one container per (harness × exercise × repetition).
        All harnesses use the same LLM model (GLM 5.2 via ZAI API) through a logging proxy.
        The only variable is the harness itself — its system prompt, tool definitions, and orchestration.
      </AccordionItem>
      <AccordionItem title="What metrics are measured?">
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Success Rate</strong> — percentage of tasks where all tests pass</li>
          <li><strong>pass@k</strong> — percentage of exercises solved at least once in k repetitions</li>
          <li><strong>Tokens</strong> — input/output tokens per task (from API usage data)</li>
          <li><strong>LLM Calls</strong> — API requests per task</li>
          <li><strong>System Prompt</strong> — token overhead of the harness's system prompt</li>
          <li><strong>Tool Schemas</strong> — token overhead of tool/function definitions</li>
          <li><strong>Prefix Stable</strong> — whether the system prompt hash stays constant within a session</li>
          <li><strong>Duration</strong> — wall-clock time per task</li>
        </ul>
      </AccordionItem>
      <AccordionItem title="Why are tool_calls missing for some harnesses?">
        Some harnesses (grok, junie, cline, kimi, autohand) emit token-level streaming deltas
        in their JSON output instead of structured tool-call events. The proxy captures the actual
        API requests and responses, but tool call counting from event streams is not possible
        for these formats. Displayed as "—" instead of misleading "0".
      </AccordionItem>
      <AccordionItem title="How to reproduce">
        <pre className="bg-zinc-950 rounded-lg p-3 text-xs overflow-x-auto"><code>{`git clone --recurse-submodules \\
  https://github.com/tufantunc/harness-benchmark.git
cd harness-benchmark
cp .env.example .env  # add your LLM_API_KEY
./scripts/build-image.sh
./scripts/benchmark.sh --abort-after 0`}</code></pre>
      </AccordionItem>
      <AccordionItem title="Limitations">
        <ul className="list-disc list-inside space-y-1">
          <li>Single LLM model (GLM 5.2) — results may differ with other models</li>
          <li>No cost data — ZAI API does not report cost in usage responses</li>
          <li>Cache write/read tokens not reported by ZAI API</li>
          <li>Tool call counts unavailable for 5 of 8 harnesses (event format limitations)</li>
          <li>Exercises are Exercism practice problems — real-world engineering tasks may produce different rankings</li>
        </ul>
      </AccordionItem>
    </div>
  );
}
