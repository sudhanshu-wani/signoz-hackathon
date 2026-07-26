# Track 01 — YouTube demo script (≤3 min)

Covers the form's points: About / Tech stack & architecture / Demo / Learning.
Pre-roll: SigNoz up via Foundry, Ollama running, proxy started, dashboards applied.

## 0:00–0:25 — About (the problem)
"Your AI usage is scattered — scripts, IDEs, agents, local models — and you have
no idea what it costs or how it behaves. The usual fix is an LLM-observability
SaaS, which means shipping your prompts to someone else's cloud. Here's the
self-hosted alternative: one line of config, and all of it lands in SigNoz on
your own machine."

## 0:25–0:55 — Tech stack & architecture
"A tiny FastAPI proxy that speaks the OpenAI API. Your app points its base URL at
localhost:8900; the proxy forwards to the real upstream — cloud or local Ollama —
and emits OpenTelemetry GenAI spans and metrics to self-hosted SigNoz, deployed
via Foundry. No SDK, no code change, any language." (Show the one-line diagram:
app → proxy → upstream, with the OTLP arrow to SigNoz.)

## 0:55–2:15 — Demo
1. Show `.env`: `OPENAI_BASE_URL=http://localhost:8900/v1` — "this is the entire
   integration."
2. `python scripts/generate_traffic.py --n 50` — real calls to real Ollama.
3. SigNoz dashboard: **cost by model** ticking up live, request rate, P95
   latency, tokens. Open one `gen_ai.chat` trace: model, tokens, cost on the span.
4. Trigger the **spend-spike alert** with a burst of traffic — "runaway-usage
   guard, out of the box."
5. Bonus one-liner: a plain `curl` through the proxy appears in SigNoz seconds
   later — "anything that speaks OpenAI is now observable."

## 2:15–2:45 — Learning & growth (deliver this unscripted — it's your credibility beat)
Tell the real war story in your own words, roughly:
"The hardest bug wasn't code — SigNoz silently drops all telemetry until the
first admin account exists, because the collector can't register with the server
without an org. Port open, containers healthy, thirty successful requests,
nothing in the UI. Found it in the server logs: 'cannot create agent without
orgId'. And our first spans were all zero milliseconds long — we measured the
upstream call first and opened the span after, so we had to stamp explicit
start and end timestamps. Now the traces show the truth: five to sixteen
seconds per call on a small local model."

## 2:45–3:00 — Close
"One line of config, your own SigNoz, every AI call observable. Repo and Foundry
casting files linked — reproduce it in minutes. Thanks."

## Capture checklist
- `.env` one-liner · traffic generator running · dashboard populating live
- one expanded gen_ai.chat span (tokens + cost) · the fired spend alert
- the curl one-liner appearing in SigNoz
