# Video transcript — word-for-word narration (~2:50 at normal pace)

*[Brackets] = what's on screen. Read the rest aloud. Practice once; don't rush —
2:50 leaves buffer under the 3:00 limit.*

---

**[0:00 — face camera or title slide: "One line of config. Every AI call observable."]**

Hi, I'm Sudhanshu. My AI usage is scattered across scripts, experiments, and a
local Ollama server — and until this week I couldn't tell you what any of it
cost, how slow it was, or how often it failed. The usual fix is an LLM
observability SaaS — which means sending your prompts to someone else's cloud.

So for Agents of SigNoz, I built the self-hosted answer: a small proxy that
makes every LLM call on your machine observable — with one line of config.

**[0:25 — show architecture diagram, then .env with OPENAI_BASE_URL=http://localhost:8900/v1]**

Here's the whole integration: your app points its OpenAI base URL at the proxy.
That's it. The proxy forwards every request to the real upstream — a cloud API
or local Ollama — and on the way back it reads the model and token usage,
computes the cost, and emits OpenTelemetry spans and metrics into SigNoz,
self-hosted on my laptop and deployed with Foundry, so judges can reproduce this
exact setup from the casting files in the repo. No SDK. No code changes. Any
language.

**[0:55 — terminal left, dashboard right. Run: python scripts/generate_traffic.py --n 20 --mix]**

Let's see it live. I'm sending real requests through the proxy to two real local
models — a 3-billion and a 1-billion parameter model. Watch the dashboard: cost
in dollars, requests per minute per model, P95 latency — you can see the smaller
model is faster — and this panel answers the question every team actually asks:
which *feature* is burning the money. Search is our expensive feature here.

**[1:30 — run: python scripts/generate_traffic.py --n 20 --mix --chaos 0.3]**

Now let's break production. I'm injecting real failures — a slice of requests
asking for a model that doesn't exist. Nothing here is fabricated; these are
genuine 404s from the upstream. And there it is — the error-rate panel goes red.

**[1:50 — SigNoz Traces: filter gen_ai.chat errors, open a failing span]**

So something's failing — where? I open the trace, and the failing span tells me
everything: model, "gpt-nonexistent", status 404, and what that call cost me.
Someone shipped a bad model name. Found in seconds, without leaving my laptop.

**[2:10 — show the spend alert firing after a --burst run]**

And for the silent failure mode — runaway spend — a SigNoz alert on the cost
metric fires when spending spikes. Real traffic tripped this one.

**[2:25 — face camera for the learning beat — keep it natural, don't read]**

The hardest bug wasn't code. SigNoz silently drops all telemetry until the first
admin account exists — thirty successful requests, port open, nothing in the UI.
I found it in the collector logs: "cannot create agent without org ID". And my
first spans were all zero milliseconds long, because I measured the call first
and opened the span after — fixed with explicit timestamps. Now the traces show
the truth: five to sixteen seconds per call on a small local GPU.

**[2:45 — repo page on screen]**

One line of config, a 150-line proxy, and self-hosted SigNoz — every AI call on
my laptop is traced, priced, and dashboarded. Repo and Foundry casting files are
linked below. Full disclosure in the repo: I built this with an AI
pair-programmer, and verified every number you just saw myself. Thanks for
watching.

---

## Recording tips
- Have drip traffic OFF during the demo (ask Claude to kill it) so panel changes
  are clearly caused by the commands you run on camera.
- Do the runs once before recording so models are warm (first load is slow).
- 2:25 learning beat: glance at the bullet points, then talk — reading kills it.
- Capture at 1080p+; zoom the browser to ~110% so panel numbers are legible.
