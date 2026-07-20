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

    # Grok events are streaming deltas — only 'end' is structured
    assert metrics.llm_calls == 1  # one 'end' event
    assert metrics.tool_calls == 0  # no tool events in streaming format
    # Token data comes from proxy, not events
    assert metrics.tokens_input == 0
    assert metrics.cost_usd == 0.0


def test_grok_message_without_usage_not_counted(tmp_path):
    """Events without 'end' should not count llm_calls."""
    events_file = tmp_path / "no-end.jsonl"
    events_file.write_text(
        '{"type":"thought","data":"thinking..."}\n'
        '{"type":"text","data":"response"}\n'
    )
    metrics = extract_metrics(events_file, format="grok")

    assert metrics.llm_calls == 0
    assert metrics.tool_calls == 0


def test_extract_junie_events(fixtures_dir):
    events_file = fixtures_dir / "junie-events.jsonl"
    metrics = extract_metrics(events_file, format="junie")

    # response + task_result have usage
    assert metrics.llm_calls == 1  # only response has usage dict
    assert metrics.tool_calls == 1
    assert metrics.tokens_input == 2800
    assert metrics.tokens_output == 320
    assert metrics.tokens_cached == 7500
    assert abs(metrics.cost_usd - 0.015) < 0.001


def test_extract_cline_events(fixtures_dir):
    events_file = fixtures_dir / "cline-events.jsonl"
    metrics = extract_metrics(events_file, format="cline")

    # 3 "say text" messages (no usage) = 3 llm_calls
    assert metrics.llm_calls == 3
    # 2 "say tool" messages = 2 tool_calls
    assert metrics.tool_calls == 2
    # No usage data in cline events
    assert metrics.tokens_input == 0
    assert metrics.cost_usd == 0.0


def test_extract_autohand_events(fixtures_dir):
    events_file = fixtures_dir / "autohand-events.jsonl"
    metrics = extract_metrics(events_file, format="autohand")

    assert metrics.llm_calls == 1  # only response has usage
    assert metrics.tool_calls == 1
    assert metrics.tokens_input == 2100
    assert metrics.tokens_output == 280
    assert metrics.tokens_cached == 6000
    assert abs(metrics.cost_usd - 0.012) < 0.001


def test_extract_kimi_events(fixtures_dir):
    events_file = fixtures_dir / "kimi-events.jsonl"
    metrics = extract_metrics(events_file, format="kimi")

    assert metrics.llm_calls == 1  # only response has usage
    assert metrics.tool_calls == 1
    assert metrics.tokens_input == 1900
    assert metrics.tokens_output == 250
    assert metrics.tokens_cached == 5500
    assert abs(metrics.cost_usd - 0.011) < 0.001
