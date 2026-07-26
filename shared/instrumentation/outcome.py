"""Outcome classification — pure policy, no OTel dependency (easy to unit test).

The crux of the cost-per-outcome thesis: a task's dollars only count if the task
actually *resolved*. This maps concrete, mostly-deterministic runtime signals to
one of three labels.

Ordering matters: a hard failure dominates a mere retry, which dominates a clean
resolve.
"""

from __future__ import annotations

from dataclasses import dataclass

from .attributes import OUTCOME_DEGRADED, OUTCOME_FAILED, OUTCOME_RESOLVED


@dataclass
class OutcomeSignals:
    tool_errored: bool = False       # any tool span raised
    exception: bool = False          # the task loop threw
    empty_answer: bool = False       # agent produced no answer
    max_retries_hit: bool = False    # loop bailed at the cap
    retry_count: int = 0             # repeated logical steps
    reask: bool = False              # user re-asked (set async, later)
    judge_failed: bool = False       # optional LLM-judge said "unresolved"


def classify_outcome(s: OutcomeSignals) -> str:
    """Deterministic mapping of signals -> outcome label."""
    if s.exception or s.tool_errored or s.empty_answer or s.max_retries_hit or s.judge_failed:
        return OUTCOME_FAILED
    if s.retry_count > 0 or s.reask:
        return OUTCOME_DEGRADED
    return OUTCOME_RESOLVED
