# AI Assistance Disclosure

Per the hackathon rules, we disclose that this project was built **with Claude
Code (Anthropic) as a pair-programming tool**, the same way we'd disclose using
an IDE or Copilot. Here is exactly how the work split, because we think the
division matters more than the label:

## What was human
- **The idea and every design decision.** The pivot to a proxy that observes
  *anyone's* AI usage (instead of building yet another agent), choosing the
  direct SigNoz REST API over the MCP server (runtime token cost), requiring all
  demo telemetry to come from real requests against a real local Ollama upstream
  (no fabricated data), and choosing a fully free/local stack so judges can
  reproduce everything without an API key.
- **Verification of every claim.** We ran the stack end-to-end and debugged it
  where it broke: SigNoz's collector silently rejects OTLP ingestion until the
  first organization exists ("cannot create agent without orgId" — found in the
  collector logs, fixed by registering and restarting the ingester); proxy spans
  initially recorded ~0ms durations (found by querying ClickHouse directly,
  fixed with explicit span start/end timestamps); the v0.134 auth API moved to
  `/api/v2/sessions/email_password` (found by reading the frontend bundle).
- **The research.** Market/pain-point research across 23 sources with
  adversarial claim-verification before deciding what to build.

## What the AI did
- Typed most of the code and tests under our direction, drafted documentation,
  and accelerated API research. Every generated component was reviewed, and the
  test suite (50 tests across the monorepo and the packaged repo) plus the live
  runs above are how we held it to account.

## What that means for the numbers you see
Every dashboard, span, and metric in the demo comes from **real HTTP requests
through the proxy to a real Ollama model on real self-hosted SigNoz** — verified
both in the SigNoz UI and by querying ClickHouse and the `query_range` API
directly. Nothing was injected or fabricated.

We used AI the way we'd want any engineer on our team to use it: as leverage,
with judgment and verification staying human.
