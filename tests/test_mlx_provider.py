"""
Integration test for the local MLX provider (Qwen3.5-9B-4bit).

Requires the MLX server to be running:
    bash models/serve.sh

Run with:
    python -m pytest tests/test_mlx_provider.py -v
    # or without pytest:
    python tests/test_mlx_provider.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from providers.mlx_provider import MLXProvider, is_available, MLX_SERVER_URL


def test_server_reachable():
    """Server responds on /v1/models."""
    r = requests.get(f"{MLX_SERVER_URL}/v1/models", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print(f"  models endpoint: {r.json()}")


def test_is_available():
    """is_available() returns True when server is up."""
    assert is_available(), "is_available() returned False — is the server running?"


def test_basic_completion():
    """Provider returns a non-empty string for a simple prompt."""
    provider = MLXProvider()
    result = provider.complete(
        system="You are a helpful assistant. Reply concisely.",
        user="What is 2 + 2? Reply with just the number.",
        max_tokens=256,
    )
    assert isinstance(result, str), "Response should be a string"
    assert len(result.strip()) > 0, "Response should not be empty"
    assert "4" in result, f"Expected '4' in response, got: {result!r}"
    print(f"  response: {result!r}")


def test_json_output():
    """Provider can return valid JSON when asked."""
    import json
    provider = MLXProvider()
    result = provider.complete(
        system="You output only valid JSON. No markdown, no explanation.",
        user='Return a JSON object with key "status" and value "ok".',
        max_tokens=256,
    )
    # Strip markdown fences if present
    raw = result.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    assert data.get("status") == "ok", f"Unexpected JSON: {data}"
    print(f"  json response: {data}")


def test_homework_generation():
    """Full homework prompt returns valid parseable JSON with expected structure."""
    import json
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from prompts import homework_prompt
    from storage import history_store
    from services.dedup_service import check_duplicates

    provider = MLXProvider()
    next_day = history_store.get_total_days() + 1
    forbidden = history_store.get_all_fingerprints()
    recent_topics = history_store.get_recent_topics(past_days=14)

    system = homework_prompt.system_prompt()
    user = homework_prompt.user_prompt(next_day, "2099-01-01", recent_topics, forbidden)

    raw = provider.complete(system=system, user=user)
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    hw = json.loads(raw)
    parts = hw.get("parts", {})
    total_q = sum(len(v) for v in parts.values())

    assert "parts" in hw, "Missing 'parts' key"
    assert total_q > 0, "No questions generated"
    assert "day" in hw, "Missing 'day' key"
    print(f"  day={hw['day']}, parts={list(parts.keys())}, questions={total_q}")


if __name__ == "__main__":
    tests = [test_server_reachable, test_is_available, test_basic_completion, test_json_output, test_homework_generation]
    passed = 0
    for t in tests:
        try:
            print(f"[RUN] {t.__name__}")
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
