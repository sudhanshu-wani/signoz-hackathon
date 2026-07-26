"""Telemetry emission for the proxy — reuses the shared OTel + pricing core.

One `gen_ai.chat` span per call plus metrics (cost, request count, latency,
tokens), all landing in SigNoz. This is the same instrumentation the rest of the
project uses, so a call captured by the proxy looks identical to one captured
in-process.
"""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.trace import Status, StatusCode

from shared.instrumentation import attributes as A
from shared.instrumentation.otel import INSTRUMENTATION_NAME, get_tracer, setup_telemetry
from shared.pricing import cost_usd

_INSTR: dict = {}


def _instruments() -> dict:
    if not _INSTR:
        setup_telemetry()
        m = metrics.get_meter(INSTRUMENTATION_NAME)
        _INSTR["cost"] = m.create_counter(A.METRIC_LLM_COST, unit="USD",
                                          description="LLM cost in USD by model")
        _INSTR["requests"] = m.create_counter("llm.requests", unit="1",
                                              description="LLM requests by model/status")
        _INSTR["latency"] = m.create_histogram("llm.request.duration", unit="ms",
                                               description="Proxy->upstream latency by model")
        _INSTR["tokens"] = m.create_counter("llm.tokens", unit="1",
                                            description="Total tokens by model")
    return _INSTR


def record_llm_call(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    status_code: int,
    error: bool = False,
    session_id: str | None = None,
    outcome: str | None = None,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
) -> float:
    """Emit a span + metrics for one observed LLM call. Returns the cost.

    The span is created retrospectively (the proxy measures the upstream call
    first), so explicit start/end timestamps make the trace view show the real
    call duration instead of ~0ms.
    """
    cost = cost_usd(model, input_tokens, output_tokens)
    tracer = get_tracer()
    span = tracer.start_span("gen_ai.chat", start_time=start_time_ns)
    try:
        span.set_attribute(A.GEN_AI_SYSTEM, "openai-compatible")
        span.set_attribute(A.GEN_AI_REQUEST_MODEL, model)
        span.set_attribute(A.GEN_AI_USAGE_INPUT_TOKENS, input_tokens)
        span.set_attribute(A.GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)
        span.set_attribute(A.LLM_COST_USD, cost)
        span.set_attribute("http.status_code", status_code)
        span.set_attribute("llm.request.duration_ms", round(duration_ms, 2))
        if session_id:
            span.set_attribute(A.SESSION_ID, session_id)
        if outcome:
            span.set_attribute(A.TASK_OUTCOME, outcome)
        if error:
            span.set_status(Status(StatusCode.ERROR))
    finally:
        span.end(end_time=end_time_ns)

    dims = {"model": model, "status": str(status_code)}
    i = _instruments()
    i["cost"].add(cost, {"model": model})
    i["requests"].add(1, dims)
    i["latency"].record(duration_ms, {"model": model})
    i["tokens"].add(input_tokens + output_tokens, {"model": model})
    return cost


def parse_usage(data: dict) -> tuple[int, int]:
    """Extract (prompt_tokens, completion_tokens) from an OpenAI-shaped response."""
    usage = (data or {}).get("usage") or {}
    return int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0)
