#!/usr/bin/env bash
# =============================================================================
# Agents of SigNoz — one-command judge demo
#
# Prerequisites (one-time, ~5 min):
#   1. SigNoz:  curl -fsSL https://signoz.io/foundry.sh | bash
#               foundryctl cast -f casting.yaml
#   2. Open http://localhost:8080 and create the admin account
#      (SigNoz silently drops telemetry until the first account exists!)
#   3. Ollama:  curl -fsSL https://ollama.com/install.sh | sh
#
# Then run:
#   SIGNOZ_EMAIL=you@example.com SIGNOZ_PASSWORD=yourpass ./judge_demo.sh
#
# The script: checks services, pulls the two small models if missing, restarts
# the SigNoz ingester (first-account gotcha), starts the proxy, imports the
# dashboard, sends REAL healthy traffic, then injects REAL failures — and tells
# you what to look at. Everything it shows comes from real requests.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf "\n\033[1;36m▸ %s\033[0m\n" "$*"; }
fail() { printf "\n\033[1;31m✗ %s\033[0m\n" "$*"; exit 1; }

say "1/7 Checking prerequisites"
command -v docker >/dev/null || fail "docker not found"
OLLAMA=$(command -v ollama || echo "$HOME/.local/ollama/bin/ollama")
[ -x "$OLLAMA" ] || fail "ollama not found — install: curl -fsSL https://ollama.com/install.sh | sh"
curl -sf http://localhost:8080 >/dev/null || fail "SigNoz UI not on :8080 — run: foundryctl cast -f casting.yaml"
curl -sf http://localhost:11434 >/dev/null || { say "starting ollama server"; nohup "$OLLAMA" serve >/dev/null 2>&1 & sleep 3; }
[ -n "${SIGNOZ_EMAIL:-}" ] && [ -n "${SIGNOZ_PASSWORD:-}" ] || \
  fail "set SIGNOZ_EMAIL and SIGNOZ_PASSWORD (the account you created at http://localhost:8080)"

say "2/7 Pulling models if missing (qwen2.5:3b + llama3.2:1b, ~3 GB total)"
"$OLLAMA" list | grep -q "qwen2.5:3b"  || "$OLLAMA" pull qwen2.5:3b
"$OLLAMA" list | grep -q "llama3.2:1b" || "$OLLAMA" pull llama3.2:1b

say "3/7 Restarting SigNoz ingester (it only registers after the first account exists)"
docker restart signoz-ingester-1 >/dev/null 2>&1 || true; sleep 8

say "4/7 Python env + tests (offline — proves the code without any services)"
if [ ! -d .venv ]; then
  command -v uv >/dev/null && uv venv -q || python3 -m venv .venv
fi
if command -v uv >/dev/null; then uv pip install -q -e ".[dev]"; else .venv/bin/pip install -q -e ".[dev]"; fi
OTEL_EXPORTER_OTLP_ENDPOINT="" .venv/bin/python -m pytest -q || fail "tests failed"

say "5/7 Starting the proxy on :8900 + importing the dashboard"
pkill -f "uvicorn proxy.server" 2>/dev/null || true; sleep 1
nohup .venv/bin/uvicorn proxy.server:app --port 8900 >/tmp/signoz-proxy.log 2>&1 &
sleep 3
curl -sf http://localhost:8900/healthz >/dev/null || fail "proxy failed to start (see /tmp/signoz-proxy.log)"
SIGNOZ_API_KEY="" .venv/bin/python proxy/dashboards/apply.py || true  # alert 400 falls back to UI; dashboard is what matters

say "6/7 REAL traffic: 16 requests across two local models (~2 min on CPU/GPU)"
.venv/bin/python scripts/generate_traffic.py --n 16 --concurrency 3 --mix

say "7/7 FAILURE INJECTION: real 404s from a nonexistent model (~1 min)"
.venv/bin/python scripts/generate_traffic.py --n 12 --concurrency 3 --mix --chaos 0.4

cat <<'EOF'

════════════════════════════════════════════════════════════════════
  DONE — open SigNoz and look at:
  1. Dashboards -> "LLM Proxy — AI usage observability"
       cost ($), requests/min by model, P95 latency, tokens,
       ERROR RATE (red from the failure injection), cost by feature
  2. Traces -> filter the failing gen_ai.chat span:
       model "gpt-nonexistent", status 404, cost on the span
  3. One-line integration check from any terminal:
       curl -s http://localhost:8900/v1/chat/completions \
         -H 'content-type: application/json' \
         -d '{"model":"qwen2.5:3b","messages":[{"role":"user","content":"hi"}]}'
     ...and watch it appear in SigNoz seconds later.

  All numbers come from real requests to real local models.
════════════════════════════════════════════════════════════════════
EOF
