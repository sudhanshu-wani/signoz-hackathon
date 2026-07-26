# Track 01 — Project description (form field)

**SigNoz LLM Observability Proxy — observe anyone's AI usage with one line of config.**

Teams run AI from everywhere — scripts, IDEs, agents, local models — with no
unified view of what it costs or how it behaves, and the popular way to get that
view is to ship your prompts to a third-party SaaS. This project is the
self-hosted, OpenTelemetry-native alternative.

It's a tiny local proxy speaking the OpenAI API. You point any app's base URL at
`http://localhost:8900/v1` — one line, any language, no SDK — and every LLM call
is forwarded to the real upstream (a cloud API or local Ollama) while its model,
token counts, cost, latency, and errors are captured into self-hosted SigNoz as
OpenTelemetry spans and metrics. A dashboard shows cost by model, request rate,
P95 latency, error rate, and tokens; an alert guards against runaway spend. An
optional `X-Session-Id` / `X-Task-Outcome` header even unlocks cost-per-outcome.

Your traffic never leaves your machine. It's the Helicone/LiteLLM pattern, but
self-hosted and OTel-native — which is exactly SigNoz's strength.

**Stack:** Python, FastAPI proxy, httpx, OpenTelemetry GenAI semantic
conventions, SigNoz (self-hosted via Foundry), dashboards + alerts via the SigNoz
REST API. Demo traffic is real (local Ollama upstream).
