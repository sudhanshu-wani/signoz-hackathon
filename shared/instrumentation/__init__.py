"""Reusable OTel GenAI instrumentation for cost-per-outcome + tool-use records.

This package is the shared core; Track 02 repackages it as a pip-installable lib.
Public API:

    from shared.instrumentation import (
        setup_telemetry, force_flush,
        task_span, llm_span, tool_span,
    )
"""

from .otel import force_flush, setup_telemetry
from .outcome import OutcomeSignals, classify_outcome
from .spans import LlmContext, TaskContext, llm_span, task_span, tool_span

__all__ = [
    "setup_telemetry",
    "force_flush",
    "task_span",
    "llm_span",
    "tool_span",
    "TaskContext",
    "LlmContext",
    "OutcomeSignals",
    "classify_outcome",
]
