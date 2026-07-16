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


def parse_pi_events(lines: list[str]) -> Metrics:
    """Parse pi --mode json output."""
    m = Metrics()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        evt_type = evt.get("type")
        if evt_type in ("message_start", "message_end"):
            msg = evt.get("message", {})
            if msg.get("role") == "assistant":
                m.llm_calls += 1
                usage = msg.get("usage", {})
                m.tokens_input += usage.get("input", 0)
                m.tokens_output += usage.get("output", 0)
                m.tokens_cached += usage.get("cacheRead", 0)
                cost = usage.get("cost", {})
                m.cost_usd += cost.get("total", 0.0)
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "toolCall":
                        m.tool_calls += 1

        elif evt_type == "tool_execution_start":
            m.tool_calls += 1

    return m


def parse_opencode_events(lines: list[str]) -> Metrics:
    """Parse opencode run --format json output."""
    m = Metrics()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        evt_type = evt.get("type", "")

        if evt_type in ("message", "message_end", "assistant"):
            usage = evt.get("usage") or evt.get("message", {}).get("usage", {})
            if usage:
                m.llm_calls += 1
                m.tokens_input += usage.get("input_tokens", usage.get("input", 0))
                m.tokens_output += usage.get("output_tokens", usage.get("output", 0))
                m.tokens_cached += usage.get("cache_read_tokens",
                                            usage.get("cached_tokens",
                                            usage.get("cacheRead", 0)))
                cost = usage.get("cost") or usage.get("total_cost", {})
                if isinstance(cost, dict):
                    m.cost_usd += cost.get("total", 0.0)
                elif isinstance(cost, (int, float)):
                    m.cost_usd += cost

        if evt_type in ("tool_start", "tool_call", "tool_execution_start"):
            m.tool_calls += 1

    return m


def parse_grok_events(lines: list[str]) -> Metrics:
    """Parse grok --output-format streaming-json output.

    Grok emits newline-delimited JSON events. Token/cost data is captured
    by the logging proxy at the API boundary (authoritative source).
    This parser provides best-effort tool_calls/llm_calls counts.
    """
    m = Metrics()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        evt_type = evt.get("type", "")

        # Grok streaming-json events: look for assistant messages and tool calls
        if evt_type in ("message", "assistant_message", "response", "turn_end"):
            m.llm_calls += 1
            usage = evt.get("usage") or evt.get("message", {}).get("usage", {})
            if usage:
                m.tokens_input += usage.get("input_tokens", usage.get("input", 0))
                m.tokens_output += usage.get("output_tokens", usage.get("output", 0))
                m.tokens_cached += usage.get("cache_read_tokens",
                                            usage.get("cached_tokens", 0))
                cost = usage.get("cost", {})
                if isinstance(cost, dict):
                    m.cost_usd += cost.get("total", 0.0)

        # Tool call patterns
        if evt_type in ("tool_call", "tool_use", "tool_execution", "action"):
            m.tool_calls += 1
        # Some events nest tool calls in content
        content = evt.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") in ("tool_use", "tool_call"):
                    m.tool_calls += 1

    return m


PARSERS = {
    "pi": parse_pi_events,
    "opencode": parse_opencode_events,
    "grok": parse_grok_events,
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
