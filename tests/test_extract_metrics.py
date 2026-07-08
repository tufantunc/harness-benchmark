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
