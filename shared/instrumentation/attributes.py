"""Canonical attribute + metric names used across agent, dashboards, guardrail.

One source of truth so the emitter, the SigNoz dashboards, the outcome tagger,
and the security guardrail never drift on spelling. GenAI names follow the
OpenTelemetry GenAI semantic conventions; ``task.*`` and ``tool.*`` are our
value-add on top (this is what differentiates the Track-02 lib from
OpenLLMetry/OpenLIT, which capture tokens but not outcomes).
"""

from __future__ import annotations

# --- OTel GenAI semantic conventions (standard) ---
GEN_AI_SYSTEM = "gen_ai.system"                    # "anthropic"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
GEN_AI_TOOL_NAME = "gen_ai.tool.name"

# --- Our value-add: cost ---
LLM_COST_USD = "llm.cost_usd"                      # per LLM span
TASK_COST_USD = "task.cost_usd"                    # rolled up to the task

# --- Our value-add: outcome layer (the cost-per-outcome story) ---
TASK_OUTCOME = "task.outcome"                      # resolved | degraded | failed
TASK_RETRY_COUNT = "task.retry_count"
TASK_REASK = "task.reask"                          # set by the async enricher
TASK_FEATURE = "task.feature"
TASK_PROMPT_VERSION = "task.prompt_version"
SESSION_ID = "session.id"

# --- Our value-add: tool-use records (security guardrail reads these) ---
TOOL_NAME = "tool.name"
TOOL_ERROR = "tool.error"                          # bool
TOOL_SENSITIVE = "tool.sensitive"                  # bool: side-effecting tool
TOOL_ARGS_DIGEST = "tool.args_digest"              # short, non-PII arg summary
TASK_USER_INTENT = "task.user_intent"              # original user request text

# Outcome enum values
OUTCOME_RESOLVED = "resolved"
OUTCOME_DEGRADED = "degraded"
OUTCOME_FAILED = "failed"

# --- Metric instrument names (queried by dashboards) ---
METRIC_TASK_COST = "task.cost.usd"                 # counter, USD
METRIC_TASK_COUNT = "task.count"                   # counter, tasks
METRIC_LLM_COST = "llm.cost.usd"                   # counter, USD
METRIC_GUARDRAIL_FLAG = "guardrail.flag.count"     # counter, security flags
