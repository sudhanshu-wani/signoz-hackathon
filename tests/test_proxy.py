"""Proxy tests against the synthetic mock upstream (no Ollama/SigNoz needed)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from proxy import server
from proxy.mock_upstream import mock_transport
from proxy.telemetry import parse_usage


@pytest.fixture
def client(monkeypatch):
    # Point the proxy's upstream client at the synthetic mock.
    server.client = httpx.AsyncClient(transport=mock_transport(), base_url="http://mock/v1")
    return TestClient(server.app)


def test_parse_usage_reads_openai_shape():
    assert parse_usage({"usage": {"prompt_tokens": 11, "completion_tokens": 4}}) == (11, 4)
    assert parse_usage({}) == (0, 0)
    assert parse_usage({"usage": None}) == (0, 0)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_proxy_passthrough_and_records(client, monkeypatch):
    captured = {}
    real = server.record_llm_call

    def spy(**kw):
        captured.update(kw)
        return real(**kw)

    monkeypatch.setattr(server, "record_llm_call", spy)

    r = client.post("/v1/chat/completions", json={
        "model": "qwen2.5:3b",
        "messages": [{"role": "user", "content": "hello there friend"}],
    }, headers={"x-session-id": "sess-1", "x-feature": "search"})

    assert r.status_code == 200
    assert r.json()["usage"]["prompt_tokens"] > 0            # passthrough intact
    assert captured["model"] == "qwen2.5:3b"
    assert captured["input_tokens"] > 0                       # usage extracted
    assert captured["session_id"] == "sess-1"                # header propagated
    assert captured["feature"] == "search"                   # feature label propagated
    assert captured["error"] is False


def test_proxy_upstream_error_is_recorded(monkeypatch):
    def failing(_req):
        return httpx.Response(500, json={"error": {"message": "boom"}})

    server.client = httpx.AsyncClient(transport=httpx.MockTransport(failing), base_url="http://mock/v1")
    captured = {}
    monkeypatch.setattr(server, "record_llm_call", lambda **kw: captured.update(kw))

    r = TestClient(server.app).post("/v1/chat/completions", json={"model": "m", "messages": []})
    assert r.status_code == 500
    assert captured["error"] is True
