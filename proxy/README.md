# SigNoz LLM Observability Proxy

**Agents of SigNoz · Track 01 — AI & Agent Observability**

> Observe **anyone's** AI usage on their laptop with **one line of config**. Point
> your app's base URL at this proxy and every LLM call — cloud or local Ollama —
> flows into self-hosted SigNoz: model, tokens, **cost**, latency, errors. No SDK,
> no code change, any language. The Helicone/LiteLLM pattern, self-hosted and
> OpenTelemetry-native.

## Why it matters
Teams run AI from a dozen places — scripts, IDEs, agents, local models — and have
zero unified view of what it costs or how it behaves. Hosted LLM-observability
SaaS means shipping your prompts to a third party. This is a self-hosted,
OTel-native alternative: your traffic, your box, your SigNoz.

## One-line integration
```bash
# anything that speaks the OpenAI API — just change the base URL:
export OPENAI_BASE_URL=http://localhost:8900/v1
# or in code: OpenAI(base_url="http://localhost:8900/v1")
```
Works with cloud APIs (set `UPSTREAM_BASE_URL` + `UPSTREAM_API_KEY`) and local
Ollama (`UPSTREAM_BASE_URL=http://localhost:11434/v1`, no key).

## Run it
```bash
cp .env.example .env                     # set UPSTREAM_BASE_URL, SIGNOZ_*
uv venv && uv pip install -e ".[dev]"
uvicorn proxy.server:app --port 8900     # start the proxy
python proxy/dashboards/apply.py         # dashboards + cost-spike alert
python scripts/generate_traffic.py --n 50   # real traffic -> real telemetry
#  open SigNoz -> "LLM Proxy" dashboard
```

## What lands in SigNoz
- **Span** per call (`gen_ai.chat`): model, input/output tokens, `llm.cost_usd`,
  latency, HTTP status — OTel GenAI semantic conventions.
- **Metrics:** `llm.cost.usd`, `llm.requests` (by model/status),
  `llm.request.duration` (histogram), `llm.tokens`.
- **Dashboard:** cost by model, request rate, P95 latency, error rate, tokens
  (`dashboards/panels.md`).
- **Alert:** runaway-spend guard on `llm.cost.usd`.

## Optional: cost-per-outcome
Send `X-Session-Id` and `X-Task-Outcome` headers and the proxy tags spans so you
can slice cost by resolved/degraded/failed — a path to $/resolved-task without
changing the proxy.

## Honest notes
- **Non-streaming** is fully captured now; streaming (`stream:true`) passes
  through but usage isn't parsed yet (documented follow-up).
- **Cost** uses `shared/pricing.py`; local-model prices are a labeled
  equivalent-hosted projection (running local is ~$0).
- Demo telemetry is **real** — actual calls through the proxy to real Ollama; the
  mock upstream (`proxy/mock_upstream.py`) is only for dependency-free tests.

## Verify (no Ollama/SigNoz needed)
```bash
pytest -q tests/test_proxy.py
```
