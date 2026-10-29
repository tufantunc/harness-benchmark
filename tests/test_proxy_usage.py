# tests/test_proxy_usage.py
"""Usage extraction in container/proxy.js, driven through node."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROXY = Path(__file__).resolve().parent.parent / "container" / "proxy.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def extract(body: str, content_type: str = "") -> dict | None:
    script = (
        f"const {{ extractUsage }} = require({json.dumps(str(PROXY))});"
        "let b = ''; process.stdin.on('data', d => b += d);"
        f"process.stdin.on('end', () => console.log(JSON.stringify(extractUsage(Buffer.from(b), {json.dumps(content_type)}))));"
    )
    out = subprocess.run(["node", "-e", script], input=body, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def sse(*chunks: dict) -> str:
    return "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"


def test_openai_chat_sse_cached_tokens():
    body = sse(
        {"choices": [{"index": 0, "delta": {"content": "hi"}}]},
        {"choices": [], "usage": {"prompt_tokens": 4304, "completion_tokens": 20,
                                  "prompt_tokens_details": {"cached_tokens": 4288}}},
    )
    u = extract(body, "text/event-stream")
    assert u["input_tokens"] == 4304  # prompt_tokens already includes the cache hits
    assert u["cache_read_tokens"] == 4288


def test_openai_chat_json_cached_tokens():
    body = json.dumps({"usage": {"prompt_tokens": 120, "completion_tokens": 5,
                                 "prompt_tokens_details": {"cached_tokens": 50}}})
    assert extract(body, "application/json")["cache_read_tokens"] == 50


def test_openai_chat_without_cache_details():
    body = sse({"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
    assert extract(body)["cache_read_tokens"] == 0


def test_anthropic_sse_cache_inclusive_input():
    # message_delta carries the full cumulative usage (shape seen in claude runs);
    # input_tokens is made cache-inclusive to match OpenAI prompt_tokens
    body = sse(
        {"type": "message_start", "message": {"usage": {"input_tokens": 2746, "output_tokens": 1,
                                                        "cache_read_input_tokens": 13504}}},
        {"type": "message_delta", "usage": {"input_tokens": 2746, "output_tokens": 94,
                                            "cache_read_input_tokens": 13504}},
    )
    assert extract(body, "text/event-stream") == {
        "input_tokens": 2746 + 13504, "output_tokens": 94,
        "cache_read_tokens": 13504, "cache_write_tokens": 0,
    }


def test_responses_api_unchanged():
    body = sse({"type": "response.completed", "response": {"usage": {
        "input_tokens": 900, "output_tokens": 30, "input_tokens_details": {"cached_tokens": 640}}}})
    assert extract(body)["cache_read_tokens"] == 640
