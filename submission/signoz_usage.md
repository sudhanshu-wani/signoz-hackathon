# Track 01 — "Describe how you used SigNoz" (form field)

SigNoz is the entire backend — the proxy exists to feed it:

- **Traces (OTel GenAI semconv):** every observed call is a `gen_ai.chat` span
  with `gen_ai.request.model`, `gen_ai.usage.input/output_tokens`, computed
  `llm.cost_usd`, latency, and HTTP status. Errors set span status = ERROR.
- **Metrics:** `llm.cost.usd` (by model), `llm.requests` (by model/status),
  `llm.request.duration` histogram (by model), `llm.tokens` (by model) — exported
  via OTLP to SigNoz.
- **Dashboards:** an "LLM Proxy" dashboard (cost by model, request rate, P95
  latency, error rate, tokens) created through the SigNoz REST API
  (`/api/v2/dashboards`). Authoritative spec in `proxy/dashboards/panels.md`.
- **Alerts:** a runaway-spend alert on `llm.cost.usd` via `/api/v1/rules`.
- **Query API:** verification reads back `llm.cost.usd` / `llm.requests` via
  `POST /api/v5/query_range` to confirm real telemetry landed.
- **Deployment:** SigNoz self-hosted via **Foundry** — `casting.yaml` +
  `casting.yaml.lock` committed so judges can reproduce the exact deploy.

We chose the **REST API over the MCP server** for programmatic access: MCP loads
many verbose tool schemas and returns large payloads into an LLM's context,
costing tokens; the direct API lets us request and trim exactly what we need.
