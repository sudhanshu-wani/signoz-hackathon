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

## 0:55–2:15 — Demo (the incident arc — this is what wins)
1. Show `.env`: `OPENAI_BASE_URL=http://localhost:8900/v1` — "this is the entire
   integration."
2. **Healthy state**: `generate_traffic.py --n 20 --mix` — two real Ollama
   models; dashboard shows cost by model, **cost by feature** ("search is our
   expensive feature"), P95 comparison between models.
3. **Incident**: `generate_traffic.py --n 20 --mix --chaos 0.3` — "something
   just broke in prod." The **error-rate panel goes red** on camera. These are
   real 404s from failure injection, and say so: "I'm injecting real failures —
   nothing here is fabricated."
4. **Root cause in seconds**: open Traces, filter `gen_ai.chat` with errors,
   open the failing span: model `gpt-nonexistent`, status 404. "Someone shipped
   a bad model name. Found it without leaving my laptop."
5. **The guard**: `--burst` trips the spend-spike alert with real traffic.

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
