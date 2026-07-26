"""OpenAI-compatible observability proxy.

Point any app's base URL at this (e.g. `OPENAI_BASE_URL=http://localhost:8900/v1`)
and every chat completion it makes is forwarded to the real upstream and captured
into SigNoz: model, tokens, cost, latency, errors. One line of config, any
language, works with cloud APIs and local Ollama alike.

    uvicorn proxy.server:app --port 8900
"""

from __future__ import annotations

import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import upstream_api_key, upstream_base_url
from .telemetry import parse_usage, record_llm_call

app = FastAPI(title="SigNoz LLM Observability Proxy")

# Module-level client so tests can swap in an httpx MockTransport.
client = httpx.AsyncClient(base_url=upstream_base_url(), timeout=120.0)


def _forward_headers(request: Request) -> dict:
    headers = {"content-type": "application/json"}
    key = upstream_api_key()
    if key:
        headers["authorization"] = f"Bearer {key}"
    return headers


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "upstream": upstream_base_url()}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "unknown")
    session_id = request.headers.get("x-session-id")
    outcome = request.headers.get("x-task-outcome")
    feature = request.headers.get("x-feature")

    t0 = time.perf_counter()
    start_ns = time.time_ns()
    try:
        upstream = await client.post(
            "/chat/completions", json=body, headers=_forward_headers(request)
        )
    except Exception as e:  # upstream unreachable
        duration_ms = (time.perf_counter() - t0) * 1000
        record_llm_call(model=model, input_tokens=0, output_tokens=0,
                        duration_ms=duration_ms, status_code=502, error=True,
                        session_id=session_id, outcome=outcome, feature=feature,
                        start_time_ns=start_ns, end_time_ns=time.time_ns())
        return JSONResponse(status_code=502, content={"error": {"message": str(e)}})

    duration_ms = (time.perf_counter() - t0) * 1000
    end_ns = time.time_ns()
    try:
        data = upstream.json()
    except Exception:
        data = None

    if isinstance(data, dict):
        in_tok, out_tok = parse_usage(data)
        record_llm_call(
            model=data.get("model", model),
            input_tokens=in_tok, output_tokens=out_tok,
            duration_ms=duration_ms, status_code=upstream.status_code,
            error=upstream.status_code >= 400, session_id=session_id, outcome=outcome,
            feature=feature, start_time_ns=start_ns, end_time_ns=end_ns,
        )
        return JSONResponse(status_code=upstream.status_code, content=data)

    # Non-JSON (e.g. streaming) — record with unknown usage, pass through text.
    record_llm_call(model=model, input_tokens=0, output_tokens=0,
                    duration_ms=duration_ms, status_code=upstream.status_code,
                    error=upstream.status_code >= 400, session_id=session_id, outcome=outcome,
                    feature=feature, start_time_ns=start_ns, end_time_ns=end_ns)
    return JSONResponse(status_code=upstream.status_code, content={"raw": upstream.text})
