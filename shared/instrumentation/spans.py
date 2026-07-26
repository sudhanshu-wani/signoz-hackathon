"""Span helpers: the API the agent (and any user of the lib) actually calls.

    with task_span(session_id, feature, prompt_version, model, user_intent) as task:
        with llm_span(model) as llm:
            resp = client.messages.create(...)
            llm.record_usage(in_tok, out_tok, finish_reason)
        with tool_span("get_order_status", sensitive=False) as tool:
            ...                      # raising inside marks the task tool-errored
        task.note_retry()            # when the loop repeats a step
        task.set_answer(text)        # empty/None -> failure signal

On exit the task span classifies its outcome from accumulated signals, stamps
``task.*`` attributes, and emits the ``task.count`` / ``task.cost.usd`` metrics
that power the dashboards. Cost and tool-use records roll up automatically via a
contextvar, so nested calls need no plumbing.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager

from opentelemetry.trace import Status, StatusCode

from ..pricing import cost_usd
from . import attributes as A
from .otel import get_instrument, get_tracer
from .outcome import OutcomeSignals, classify_outcome

_CURRENT_TASK: contextvars.ContextVar["TaskContext | None"] = contextvars.ContextVar(
    "current_task", default=None
)


class TaskContext:
    def __init__(self, span, *, model, feature, prompt_version, session_id):
        self._span = span
        self.model = model
        self.feature = feature
        self.prompt_version = prompt_version
        self.session_id = session_id
        self.cost_usd = 0.0
        self.signals = OutcomeSignals()
        self._outcome_override: str | None = None

    # --- accumulators, called by llm_span / tool_span / the agent loop ---
    def add_cost(self, usd: float) -> None:
        self.cost_usd = round(self.cost_usd + usd, 6)

    def note_retry(self, n: int = 1) -> None:
        self.signals.retry_count += n

    def note_tool_error(self) -> None:
        self.signals.tool_errored = True

    def set_max_retries_hit(self) -> None:
        self.signals.max_retries_hit = True

    def set_answer(self, text: str | None) -> None:
        self.signals.empty_answer = not bool(text and text.strip())

    def set_judge_failed(self, failed: bool) -> None:
        self.signals.judge_failed = failed

    def set_outcome(self, outcome: str) -> None:
        """Explicit override; otherwise the outcome is classified on exit."""
        self._outcome_override = outcome

    @property
    def outcome(self) -> str:
        return self._outcome_override or classify_outcome(self.signals)


@contextmanager
def task_span(
    *,
    session_id: str,
    feature: str,
    prompt_version: str,
    model: str,
    user_intent: str = "",
):
    tracer = get_tracer()
    with tracer.start_as_current_span("agent.task") as span:
        span.set_attribute(A.SESSION_ID, session_id)
        span.set_attribute(A.TASK_FEATURE, feature)
        span.set_attribute(A.TASK_PROMPT_VERSION, prompt_version)
        span.set_attribute(A.GEN_AI_REQUEST_MODEL, model)
        if user_intent:
            span.set_attribute(A.TASK_USER_INTENT, user_intent[:2000])
        ctx = TaskContext(
            span,
            model=model,
            feature=feature,
            prompt_version=prompt_version,
            session_id=session_id,
        )
        token = _CURRENT_TASK.set(ctx)
        try:
            yield ctx
        except Exception:
            ctx.signals.exception = True
            span.set_status(Status(StatusCode.ERROR))
            _finalize(ctx)
            _CURRENT_TASK.reset(token)
            raise
        _finalize(ctx)
        _CURRENT_TASK.reset(token)


def _finalize(ctx: TaskContext) -> None:
    outcome = ctx.outcome
    span = ctx._span
    span.set_attribute(A.TASK_OUTCOME, outcome)
    span.set_attribute(A.TASK_COST_USD, ctx.cost_usd)
    span.set_attribute(A.TASK_RETRY_COUNT, ctx.signals.retry_count)
    dims = {
        "model": ctx.model,
        "outcome": outcome,
        "prompt_version": ctx.prompt_version,
        "feature": ctx.feature,
    }
    get_instrument("task_count").add(1, dims)
    get_instrument("task_cost").add(ctx.cost_usd, dims)


class LlmContext:
    def __init__(self, span, model):
        self._span = span
        self.model = model

    def record_usage(
        self, input_tokens: int, output_tokens: int, finish_reason: str | None = None
    ) -> float:
        cost = cost_usd(self.model, input_tokens, output_tokens)
        self._span.set_attribute(A.GEN_AI_USAGE_INPUT_TOKENS, input_tokens)
        self._span.set_attribute(A.GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)
        self._span.set_attribute(A.LLM_COST_USD, cost)
        if finish_reason:
            self._span.set_attribute(A.GEN_AI_RESPONSE_FINISH_REASONS, [finish_reason])
        get_instrument("llm_cost").add(cost, {"model": self.model})
        task = _CURRENT_TASK.get()
        if task is not None:
            task.add_cost(cost)
        return cost


@contextmanager
def llm_span(model: str):
    tracer = get_tracer()
    with tracer.start_as_current_span("gen_ai.chat") as span:
        span.set_attribute(A.GEN_AI_SYSTEM, "anthropic")
        span.set_attribute(A.GEN_AI_REQUEST_MODEL, model)
        yield LlmContext(span, model)


@contextmanager
def tool_span(name: str, *, sensitive: bool = False, args_digest: str = ""):
    tracer = get_tracer()
    with tracer.start_as_current_span(f"tool.{name}") as span:
        span.set_attribute(A.TOOL_NAME, name)
        span.set_attribute(A.GEN_AI_TOOL_NAME, name)
        span.set_attribute(A.TOOL_SENSITIVE, sensitive)
        if args_digest:
            span.set_attribute(A.TOOL_ARGS_DIGEST, args_digest[:500])
        try:
            yield span
        except Exception:
            span.set_attribute(A.TOOL_ERROR, True)
            span.set_status(Status(StatusCode.ERROR))
            task = _CURRENT_TASK.get()
            if task is not None:
                task.note_tool_error()
            raise
