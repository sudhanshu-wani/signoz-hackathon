# I made every LLM call on my laptop observable with one line of config

*(Draft for Dev.to / Medium / Substack — personalize the voice, add your
screenshots at the marked slots, and publish. ~1,300 words. Everything below
actually ran; numbers are from the real setup.)*

---

My AI usage is scattered across scripts, experiments, and a local Ollama server
— and until last week I could not have told you what any of it cost, how slow it
was, or how often it silently failed. The tools that answer those questions
(Helicone, LangSmith, and friends) mostly answer them by shipping your prompts
to someone else's cloud.

For the Agents of SigNoz hackathon I built the self-hosted version of that
answer: a ~150-line proxy that sits between any app and any LLM, and turns every
call into OpenTelemetry traces and metrics inside SigNoz running on my own
laptop. Integration is genuinely one line:

```bash
export OPENAI_BASE_URL=http://localhost:8900/v1
```

Anything that speaks the OpenAI API — which today means almost everything,
including local Ollama — is now observable: model, token counts, dollar cost,
latency, and errors, in dashboards I own.

## The idea

I started the hackathon building something much more complicated: an
instrumented AI agent with a two-model cost comparison. Halfway through, I asked
a better question: *why am I building an AI for people to observe, when everyone
already has AI usage and nobody can see it?*

So I threw the agent away. The replacement is boring in the best way — a FastAPI
passthrough:

1. Your app calls `POST /v1/chat/completions` on the proxy.
2. The proxy forwards the body to the real upstream (`UPSTREAM_BASE_URL` — an
   Ollama `/v1` endpoint in my case, but any OpenAI-compatible API works).
3. On the way back it reads `model` and the `usage` block, computes cost from a
   pricing table, and emits one `gen_ai.chat` span (OTel GenAI semantic
   conventions) plus four metrics: `llm.cost.usd`, `llm.requests`,
   `llm.request.duration`, `llm.tokens`.
4. OTLP carries all of it to self-hosted SigNoz.

No SDK. No code change. Language-agnostic, because the integration point is a
URL.

**[SCREENSHOT 1: the SigNoz dashboard — cost by model, request rate, P95
latency, tokens — populated with real traffic]**

## Deploying SigNoz the reproducible way

The hackathon requires deploys via Foundry, SigNoz's new declarative CLI, and it
turned out to be the nicest part of the setup. One file (`casting.yaml`, seven
lines) declares the deployment; one command brings it up:

```bash
curl -fsSL https://signoz.io/foundry.sh | bash
foundryctl cast -f casting.yaml
```

`cast` validates your tooling, generates the compose files, starts the stack,
and writes a `casting.yaml.lock` with checksums — so anyone (including the
judges) can reproduce my exact deployment.

## Three things that broke, and how I found them

This is the part no quickstart tells you about.

### 1. OTLP ingestion is silently dead until the first user exists

My first traffic run looked perfect — `30/30 ok` — and SigNoz showed *nothing*.
The proxy logs said the OTLP exporter was being refused:

```
StatusCode.UNAVAILABLE ... Connection reset by peer
```

Port 4317 was open. The collector container said "Everything is ready." I only
found the real cause in the SigNoz server logs:

```
"failed to find or create agent" ... "cannot create agent without orgId"
```

SigNoz's collector gets its pipeline configuration from the server via OpAMP —
and the server refuses to register it until an organization exists, which only
happens when the **first admin account is created**. Register in the UI, restart
the ingester, and telemetry flows. Nothing in the ingestion path tells you this;
the receiver just resets your connections.

**[SCREENSHOT 2: a gen_ai.chat trace in SigNoz showing model, token counts, and
llm.cost_usd attributes]**

### 2. My spans were all 0ms long

Once data flowed, I verified it straight in ClickHouse (SigNoz's storage — you
can `docker exec` into it and query, which is a fantastic debugging loop):

```sql
SELECT attributes_string['gen_ai.request.model'] AS model,
       round(duration_nano/1e6) AS span_ms
FROM signoz_traces.signoz_index_v3 WHERE name='gen_ai.chat'
```

Every span: `0ms`. The bug was mine: the proxy measures the upstream call
*first* and records the span *afterwards*, so the span opened and closed within
microseconds. The fix is OTel's explicit timestamps — capture `time.time_ns()`
before and after the upstream call, then create the span retrospectively:

```python
span = tracer.start_span("gen_ai.chat", start_time=start_ns)
...
span.end(end_time=end_ns)
```

After that, the trace view showed the truth: my `qwen2.5:3b` calls take 5–16
seconds under concurrency on a 6 GB laptop GPU. Which is exactly the kind of
thing you want a trace view to tell you.

### 3. The login API isn't where the docs say

I wanted to create dashboards programmatically. In SigNoz v0.134, `POST
/api/v1/login` returns… the frontend's HTML (the SPA catch-all). I ended up
grepping the minified frontend bundle for the route the UI itself uses, and
found it: `POST /api/v2/sessions/email_password`, which also requires the
`orgID`. With that token, dashboard creation worked first try —

```
POST /api/v1/dashboards  ->  201
```

— and SigNoz even auto-migrated my dashboard JSON to its newer internal schema.
(The alert-rules API rejected every payload variant I tried; I created that one
alert in the UI and moved on. Sometimes the pragmatic answer is a mouse.)

## Did it work? Prove it.

The claim "everything is observable" should itself be observable. Two checks:

- The query API returns real aggregates:
  `POST /api/v4/query_range` → `llm.cost.usd` grouped by model → one series,
  `qwen2.5:3b`, with a nonzero dollar value.
- ClickHouse shows one `gen_ai.chat` span per request with real durations and
  per-call costs in the `$0.00001–$0.0002` range (local model, priced against a
  clearly-labeled equivalent-hosted reference — running locally is ~free, which
  is rather the point).

**[SCREENSHOT 3: terminal — generate_traffic.py output next to the query_range
JSON response]**

## Takeaways

- **The base URL is the best integration point in AI tooling.** Everything
  speaks the OpenAI API, so a proxy gets you observability across every
  language and tool at once — no SDK adoption problem.
- **OTel's GenAI semantic conventions are ready.** Standard attribute names for
  model and token usage meant SigNoz's UI understood my spans with zero custom
  configuration — and any OTLP backend would.
- **Verify at the storage layer.** Querying ClickHouse directly caught a bug
  (0ms spans) that the metrics dashboards would have hidden forever.
- **First-run state is the sharpest edge in self-hosted tools.** "Works after
  you create an account" is fine; *silently dropping telemetry* until you create
  an account cost me an hour. Check the server logs, not just the client's.
- Disclosure: I built this with an AI pair-programmer (Claude Code) doing much
  of the typing, with the design decisions, debugging, and every verification
  step above done by me. The numbers in this post come from real runs.

## Wrap-up

One line of config, a small proxy, and self-hosted SigNoz: every LLM call on my
laptop is now traced, priced, and dashboarded. Repo (with the Foundry casting
files to reproduce the deploy): **github.com/sudhanshu-netbeam/signoz-llm-proxy**
— and SigNoz's self-host docs are at signoz.io/docs if you want the same
visibility into your own AI usage.
