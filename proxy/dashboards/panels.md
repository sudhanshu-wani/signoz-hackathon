# LLM Proxy dashboard — authoritative panel spec

Source of truth. If `dashboard.json` won't import on your SigNoz version, build
these in the UI (~3 min) and export.

Metrics emitted by the proxy (`proxy/telemetry.py`):
- `llm.cost.usd`         — counter (USD), label `model`
- `llm.requests`         — counter, labels `model`, `status`
- `llm.request.duration` — histogram (ms), label `model`
- `llm.tokens`           — counter, label `model`

## Panels
1. **Cost over time** — `sum(rate(llm.cost.usd))` timeseries (all models). The live spend of everything flowing through the proxy.
2. **Cost by model** — `sum(llm.cost.usd)` group by `model`. Which model is eating budget.
3. **Request rate** — `sum(rate(llm.requests))` group by `model`.
4. **Error rate** — `sum(llm.requests{status!="200"}) / sum(llm.requests)` group by `model`.
5. **Latency P95** — P95 of `llm.request.duration` group by `model`. Model vs model speed.
6. **Tokens by model** — `sum(llm.tokens)` group by `model`.

## Alert (see cost_spike_alert.json)
Fire when `sum(llm.cost.usd)` over 5m crosses a budget threshold — a runaway-spend
guard for anyone's local AI usage.
