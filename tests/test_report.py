# tests/test_report.py
import json
from pathlib import Path

from benchmark.store import Store, RunResult
from benchmark.report import compute_leaderboard, generate_markdown


def _seed(store: Store, harness: str, success: bool, cost: float, tokens: int):
    store.upsert(RunResult(
        run_id="t1", harness=harness, model="glm-5.2", language="python",
        exercise="test-ex", repetition=1, success=success,
        tokens_input=tokens, tokens_output=0, tokens_cached=0,
        cost_usd=cost, duration_sec=10.0, tool_calls=5, llm_calls=3,
        diff_loc=20, timed_out=False, tampered=False, artifact_path="",
    ))


def test_compute_leaderboard(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()
    _seed(store, "opencode", True, 0.01, 5000)
    _seed(store, "pi", False, 0.02, 8000)

    lb = compute_leaderboard(store, model="glm-5.2")

    assert len(lb) == 2
    assert lb[0]["harness"] == "opencode"
    assert lb[0]["success_rate"] == 1.0
    assert lb[1]["harness"] == "pi"
    assert lb[1]["success_rate"] == 0.0


def test_generate_markdown(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()
    _seed(store, "opencode", True, 0.01, 5000)
    _seed(store, "pi", True, 0.02, 8000)

    lb = compute_leaderboard(store, model="glm-5.2")
    md = generate_markdown(lb, model="glm-5.2")

    assert "| opencode |" in md
    assert "| pi |" in md
    assert "glm-5.2" in md


def test_leaderboard_reports_served_model(tmp_path):
    """compute_leaderboard surfaces the served model so cohort mixing is visible."""
    store = Store(tmp_path / "test.db")
    store.init_schema()
    for i, (harness, served) in enumerate([("crush", "glm-5.3"), ("cline", "glm-5.2")]):
        store.upsert(RunResult(
            run_id="b", harness=harness, model="glm-5.2", language="python",
            exercise="beer-song", repetition=1, success=True,
            tokens_input=1, tokens_output=1, tokens_cached=0, cost_usd=0.0,
            duration_sec=1.0, tool_calls=0, llm_calls=1, diff_loc=0,
            timed_out=False, tampered=False, artifact_path="a", served_model=served,
        ))

    entries = compute_leaderboard(store)
    by_harness = {e["harness"]: e for e in entries}
    assert by_harness["crush"]["served_model"] == "glm-5.3"
    assert by_harness["cline"]["served_model"] == "glm-5.2"
