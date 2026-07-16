# tests/test_extract_metrics.py
import json
from pathlib import Path

from container.extract_metrics import extract_metrics, Metrics


def test_extract_pi_events(fixtures_dir):
    events_file = fixtures_dir / "pi-events.jsonl"
    metrics = extract_metrics(events_file, format="pi")

    assert metrics.tokens_input == 4231
    assert metrics.tokens_output == 567
    assert metrics.tokens_cached == 8900
    assert abs(metrics.cost_usd - 0.023) < 0.001
    assert metrics.llm_calls == 2
    assert metrics.tool_calls == 1


def test_extract_empty_events(tmp_path):
    events_file = tmp_path / "empty.jsonl"
    events_file.write_text("")
    metrics = extract_metrics(events_file, format="pi")

    assert metrics.tokens_input == 0
    assert metrics.tokens_output == 0
    assert metrics.cost_usd == 0.0
    assert metrics.llm_calls == 0


def test_extract_grok_events(fixtures_dir):
    events_file = fixtures_dir / "grok-events.jsonl"
    metrics = extract_metrics(events_file, format="grok")

    # 2 events have usage (response + turn_end), 1 message has no usage
    assert metrics.llm_calls == 2
    # 1 tool_call event, no double-count from content nesting
    assert metrics.tool_calls == 1
    # Tokens accumulated from both usage-bearing events
    assert metrics.tokens_input == 6400
    assert metrics.tokens_output == 900
    assert metrics.tokens_cached == 16000
    # Cost only from response event (turn_end has no cost key)
    assert abs(metrics.cost_usd - 0.018) < 0.001


def test_grok_message_without_usage_not_counted(tmp_path):
    """Events matching llm type but without usage must not increment llm_calls."""
    events_file = tmp_path / "no-usage.jsonl"
    events_file.write_text(
        '{"type":"message","role":"assistant","content":[{"type":"text","text":"hi"}]}\n'
        '{"type":"turn_end","message":{"role":"assistant"}}\n'
    )
    metrics = extract_metrics(events_file, format="grok")

    assert metrics.llm_calls == 0
    assert metrics.tool_calls == 0
