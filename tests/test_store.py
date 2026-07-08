# tests/test_store.py
from benchmark.store import Store, RunResult


def test_store_insert_and_query(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()

    result = RunResult(
        run_id="batch-001",
        harness="opencode",
        model="glm-5.2",
        language="python",
        exercise="affine-cipher",
        repetition=1,
        success=True,
        tokens_input=4231,
        tokens_output=567,
        tokens_cached=8900,
        cost_usd=0.021,
        duration_sec=47.3,
        tool_calls=8,
        llm_calls=4,
        diff_loc=42,
        timed_out=False,
        tampered=False,
        artifact_path="artifacts/batch-001/opencode/python/affine-cipher/rep-1",
    )
    store.upsert(result)

    rows = store.query(harness="opencode", model="glm-5.2")
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].cost_usd == 0.021


def test_store_upsert_is_idempotent(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()

    result1 = RunResult(
        run_id="batch-001", harness="pi", model="glm-5.2", language="python",
        exercise="affine-cipher", repetition=1, success=False,
        tokens_input=100, tokens_output=50, tokens_cached=0,
        cost_usd=0.001, duration_sec=10.0, tool_calls=2, llm_calls=1,
        diff_loc=5, timed_out=False, tampered=False, artifact_path="",
    )
    store.upsert(result1)

    result2 = RunResult(
        run_id="batch-002", harness="pi", model="glm-5.2", language="python",
        exercise="affine-cipher", repetition=1, success=True,
        tokens_input=200, tokens_output=80, tokens_cached=0,
        cost_usd=0.002, duration_sec=20.0, tool_calls=3, llm_calls=2,
        diff_loc=10, timed_out=False, tampered=False, artifact_path="",
    )
    store.upsert(result2)

    rows = store.query(harness="pi", model="glm-5.2")
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].cost_usd == 0.002


def test_store_skip_existing_check(tmp_path):
    store = Store(tmp_path / "test.db")
    store.init_schema()

    result = RunResult(
        run_id="b1", harness="opencode", model="glm-5.2", language="python",
        exercise="leap", repetition=1, success=True,
        tokens_input=10, tokens_output=5, tokens_cached=0,
        cost_usd=0.001, duration_sec=5.0, tool_calls=1, llm_calls=1,
        diff_loc=3, timed_out=False, tampered=False, artifact_path="",
    )
    store.upsert(result)

    assert store.exists("opencode", "glm-5.2", "python", "leap", 1)
    assert not store.exists("opencode", "glm-5.2", "python", "leap", 2)
    assert not store.exists("pi", "glm-5.2", "python", "leap", 1)
