# harness-benchmark

Benchmark coding agent harnesses (opencode, pi, and more) against each other using an identical LLM, identical tasks, and identical isolation.

## What this measures

Two agent harnesses run the **same model** on the **same tasks** in **isolated Docker containers**. The only variable is the harness itself — its system prompt, tool orchestration, and context management.

| Dimension | Detail |
|-----------|--------|
| Task suite | [Aider Polyglot Benchmark](https://github.com/Aider-AI/polyglot-benchmark) (Exercism exercises) |
| MVP scope | Python (34 exercises) + JavaScript (49 exercises) |
| Framework | [inspect-ai](https://inspect.ai-safety-institute.org.uk/) on host |
| Isolation | Docker container per (harness × task × repetition) |
| Default model | GLM 5.2 via ZAI provider |
| Repetitions | 3 (configurable) |

## Metrics

- **Success**: do the exercise test suites pass?
- **Cost**: tokens (input/output/cached) and USD
- **Efficiency**: tool calls, LLM API calls, duration
- **Quality**: diff size, lint/type-check pass, existing-test regression

## Results

Leaderboards are published to **GitHub Pages**: <https://tufantunc.github.io/harness-benchmark/>

## Run it yourself

```bash
git clone https://github.com/tufantunc/harness-benchmark.git
cd harness-benchmark
cp .env.example .env   # add your API keys
docker build -t harness:latest .
./benchmark.sh --model glm-5.2
```

See [docs/superpowers/specs/](docs/superpowers/specs/) for the full design spec.

## Add a harness

Drop a new folder under `harnesses/<name>/` with a `manifest.yaml` and `adapter.sh`. See existing harnesses for the contract.

## License

MIT
