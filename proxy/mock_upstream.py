"""Synthetic OpenAI-compatible upstream for tests and Ollama-free demos.

Clearly synthetic: it echoes a canned reply and returns a `usage` block sized to
the prompt. The *requests* through the proxy are still real (real HTTP, real
latency), only the upstream content/tokens are synthetic. Never used to fabricate
telemetry for the actual submission — that runs against real Ollama.
"""

from __future__ import annotations

import json

import httpx


def _handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content or b"{}")
    model = body.get("model", "mock-model")
    messages = body.get("messages", []) or []
    prompt_tokens = max(1, sum(len(str(m.get("content", "")).split()) for m in messages))
    completion = "(synthetic reply from mock upstream)"
    completion_tokens = len(completion.split())
    return httpx.Response(
        200,
        json={
            "id": "mock-cmpl",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": completion},
                         "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
    )


def mock_transport() -> httpx.MockTransport:
    return httpx.MockTransport(_handler)
