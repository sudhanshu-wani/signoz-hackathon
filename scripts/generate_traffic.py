"""Drive REAL traffic through the proxy so SigNoz dashboards populate.

These are genuine HTTP calls to the proxy (which forwards to the real upstream —
local Ollama by default), producing real latency/token/cost telemetry. Only the
prompt text is canned; nothing is fabricated into SigNoz.

    python scripts/generate_traffic.py --n 50
    python scripts/generate_traffic.py --n 40 --mix              # two models
    python scripts/generate_traffic.py --n 40 --mix --chaos 0.2  # +real 404s
    python scripts/generate_traffic.py --burst                   # trip the spend alert

--chaos sends that fraction of requests to a nonexistent model: the upstream
really returns 404, so error-rate panels show REAL failures (failure injection,
not fabricated data). --burst fires a tight batch to trip the cost-spike alert
with real spend.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

PROMPTS = [
    ("chat", "What's the status of order 1001?"),
    ("chat", "My package is late, what should I do?"),
    ("search", "How long do refunds take?"),
    ("search", "Is accidental damage covered by warranty?"),
    ("search", "How much is express shipping?"),
    ("summarize", "Summarize your return policy in one sentence."),
    ("summarize", "Explain the difference between a trace and a span in one line."),
    ("chat", "Write a haiku about observability."),
]

CHAOS_MODEL = "gpt-nonexistent"  # upstream really 404s on this


def _one(base_url: str, models: list[str], chaos: float, rng: random.Random, i: int) -> tuple[int, float]:
    feature, prompt = PROMPTS[i % len(PROMPTS)]
    model = CHAOS_MODEL if rng.random() < chaos else models[i % len(models)]
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            f"{base_url}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "stream": False},
            headers={"x-session-id": f"gen-{i % 7}", "x-feature": feature},
            timeout=180.0,
        )
        return r.status_code, (time.perf_counter() - t0) * 1000
    except Exception:
        return 0, (time.perf_counter() - t0) * 1000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--proxy-url", default=os.getenv("PROXY_URL", "http://localhost:8900/v1"))
    ap.add_argument("--model", default=os.getenv("STRONG_MODEL", "qwen2.5:3b"))
    ap.add_argument("--mix", action="store_true",
                    help="alternate between STRONG_MODEL and MIX_MODEL (default llama3.2:1b)")
    ap.add_argument("--chaos", type=float, default=0.0,
                    help="fraction of requests sent to a nonexistent model (real 404s)")
    ap.add_argument("--burst", action="store_true",
                    help="tight burst (n=30, concurrency=6) to trip the spend alert")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.burst:
        args.n, args.concurrency = max(args.n, 30), 6

    models = [args.model]
    if args.mix:
        models.append(os.getenv("MIX_MODEL", "llama3.2:1b"))
    rng = random.Random(args.seed)

    print(f"Firing {args.n} requests at {args.proxy_url} "
          f"(models={models}, chaos={args.chaos}, concurrency={args.concurrency})")
    ok = err = 0
    durations = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for status, ms in pool.map(
            lambda i: _one(args.proxy_url, models, args.chaos, rng, i), range(args.n)
        ):
            durations.append(ms)
            if status == 200:
                ok += 1
            else:
                err += 1
    p50 = sorted(durations)[len(durations) // 2] if durations else 0
    print(f"done: {ok} ok, {err} failed (chaos-injected are expected failures), p50 {p50:.0f} ms")
    print("Open SigNoz -> LLM Proxy dashboard: cost/latency/tokens by model, errors, cost by feature.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
