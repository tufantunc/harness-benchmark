#!/usr/bin/env python3
"""Parse agent JSON event streams and extract normalized metrics."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Metrics:
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cached: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    llm_calls: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _iter_events(lines: list[str]):
    """Yield parsed JSON objects from newline-delimited JSON lines."""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _accumulate_usage(m: Metrics, usage: dict) -> bool:
    """Accumulate token/cost from a usage dict.

    Handles all known key variants across harnesses:
      input_tokens | input, output_tokens | output,
      cache_read_tokens | cached_tokens | cacheRead,
      cost: {total: N} | total_cost: {total: N} | cost: N (numeric)

    Returns True if usage was non-empty (i.e., an LLM call was made).
    """
    if not usage:
        return False
    m.llm_calls += 1
    m.tokens_input += usage.get("input_tokens", usage.get("input", 0))
    m.tokens_output += usage.get("output_tokens", usage.get("output", 0))
    m.tokens_cached += usage.get(
        "cache_read_tokens",
        usage.get("cached_tokens",
        usage.get("cacheRead", 0))
    )
    cost = usage.get("cost") or usage.get("total_cost", {})
    if isinstance(cost, dict):
        m.cost_usd += cost.get("total", 0.0)
    elif isinstance(cost, (int, float)):
        m.cost_usd += cost
    return True


def parse_pi_events(lines: list[str]) -> Metrics:
    """Parse pi --mode json output.

    AssistantMessage events contain a usage object with token/cost data.
    tool_execution_start events indicate tool calls.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        evt_type = evt.get("type")
        if evt_type in ("message_start", "message_end"):
            msg = evt.get("message", {})
            if msg.get("role") == "assistant":
                _accumulate_usage(m, msg.get("usage", {}))
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "toolCall":
                        m.tool_calls += 1
        elif evt_type == "tool_execution_start":
            m.tool_calls += 1
    return m


def parse_opencode_events(lines: list[str]) -> Metrics:
    """Parse opencode run --format json output.

    opencode emits step_start/step_finish/tool_use events.
    Token data is in step_finish.part.tokens with nested cache object.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        evt_type = evt.get("type", "")
        if evt_type == "step_finish":
            tokens = evt.get("part", {}).get("tokens", {})
            if tokens:
                cache = tokens.get("cache", {})
                usage = {
                    "input_tokens": tokens.get("input", 0),
                    "output_tokens": tokens.get("output", 0),
                    "cache_read_tokens": cache.get("read", 0),
                    "cache_write_tokens": cache.get("write", 0),
                }
                _accumulate_usage(m, usage)
        elif evt_type == "tool_use":
            m.tool_calls += 1
    return m


def parse_grok_events(lines: list[str]) -> Metrics:
    """Parse grok --output-format streaming-json output.

    Grok emits token-level streaming deltas (thought/text), not structured
    message events. Token/cost data is captured by the logging proxy.
    The 'end' event signals session completion.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        if evt.get("type") == "end":
            m.llm_calls += 1
    return m


def parse_junie_events(lines: list[str]) -> Metrics:
    """Parse junie --output-format json output.

    Junie outputs JSON events. Token/cost data is captured by the logging
    proxy at the API boundary (authoritative source).
    This parser provides best-effort tool_calls/llm_calls counts.

    NOTE: Event type names are best-guess until a real fixture is captured.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        evt_type = evt.get("type", "")
        if evt_type in ("message", "assistant", "response"):
            usage = evt.get("usage") or evt.get("message", {}).get("usage", {})
            _accumulate_usage(m, usage)
        elif evt_type in ("tool_call", "tool_use", "tool_execution", "command"):
            m.tool_calls += 1
    return m


def parse_cline_events(lines: list[str]) -> Metrics:
    """Parse cline --json output.

    Cline outputs {"type":"say","text":"...","ts":...,"say":"text"} messages.
    No usage/token data in events — the logging proxy is the sole source.
    This parser provides best-effort tool_calls/llm_calls counts.

    NOTE: Cline's "say" subtypes are best-guess for tool detection.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        evt_type = evt.get("type", "")
        say_sub = evt.get("say", "")

        if evt_type == "say" and say_sub in ("text", "reasoning"):
            usage = evt.get("usage")
            if usage:
                _accumulate_usage(m, usage)
            else:
                m.llm_calls += 1
        elif evt_type == "say" and say_sub in ("tool", "command", "completion_result"):
            m.tool_calls += 1
        elif evt_type == "ask" and evt.get("ask", "") == "tool":
            m.tool_calls += 1
    return m


def parse_autohand_events(lines: list[str]) -> Metrics:
    """Parse autohand -p output.

    Autohand outputs JSON events. Token/cost data is captured by the logging
    proxy at the API boundary (authoritative source).
    This parser provides best-effort tool_calls/llm_calls counts.

    NOTE: Event type names are best-guess until a real fixture is captured.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        evt_type = evt.get("type", "")
        if evt_type in ("message", "assistant", "response", "llm_response"):
            usage = evt.get("usage") or evt.get("message", {}).get("usage", {})
            _accumulate_usage(m, usage)
        elif evt_type in ("tool_call", "tool_use", "tool_execution", "action", "command"):
            m.tool_calls += 1
    return m


def parse_kimi_events(lines: list[str]) -> Metrics:
    """Parse kimi -p output.

    Kimi CLI outputs JSON events. Token/cost data is captured by the logging
    proxy at the API boundary (authoritative source).
    This parser provides best-effort tool_calls/llm_calls counts.

    NOTE: Event type names are best-guess until a real fixture is captured.
    """
    m = Metrics()
    for evt in _iter_events(lines):
        evt_type = evt.get("type", "")
        if evt_type in ("message", "assistant", "response", "chat_completion"):
            usage = evt.get("usage") or evt.get("message", {}).get("usage", {})
            _accumulate_usage(m, usage)
        elif evt_type in ("tool_call", "tool_use", "function_call", "action"):
            m.tool_calls += 1
    return m


PARSERS = {
    "pi": parse_pi_events,
    "opencode": parse_opencode_events,
    "grok": parse_grok_events,
    "junie": parse_junie_events,
    "cline": parse_cline_events,
    "autohand": parse_autohand_events,
    "kimi": parse_kimi_events,
}


def extract_metrics(events_file: Path, format: str) -> Metrics:
    parser = PARSERS.get(format)
    if parser is None:
        raise ValueError(f"Unknown format: {format}. Supported: {list(PARSERS)}")
    lines = events_file.read_text().splitlines()
    return parser(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_metrics.py <events.jsonl> <format> [output.json]", file=sys.stderr)
        sys.exit(1)
    events_file = Path(sys.argv[1])
    fmt = sys.argv[2]
    output = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    metrics = extract_metrics(events_file, fmt)
    result = metrics.to_dict()

    if output:
        output.write_text(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
