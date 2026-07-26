"""Drive REAL traffic through the proxy so SigNoz dashboards populate.

These are genuine HTTP calls to the proxy (which forwards to the real upstream —
local Ollama by default), producing real latency/token/cost telemetry. Only the
prompt text is canned; nothing is fabricated into SigNoz.

    python scripts/generate_traffic.py --n 50
    python scripts/generate_traffic.py --n 100 --concurrency 4 --model qwen2.5:3b
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

PROMPTS = [
    "What's the status of order 1001?",
    "How long do refunds take?",
    "Summarize your return policy in one sentence.",
    "Is accidental damage covered by warranty?",
    "How much is express shipping?",
    "My package is late, what should I do?",
    "Explain the difference between a trace and a span.",
    "Write a haiku about observability.",
]


def _one(base_url: str, model: str, i: int) -> tuple[int, float]:
    prompt = PROMPTS[i % len(PROMPTS)]
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            f"{base_url}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "stream": False},
            headers={"x-session-id": f"gen-{i % 7}"},  # a few sessions
            timeout=120.0,
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
    args = ap.parse_args()

    print(f"Firing {args.n} requests at {args.proxy_url} (model={args.model}, "
          f"concurrency={args.concurrency})")
    ok = 0
    durations = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for status, ms in pool.map(lambda i: _one(args.proxy_url, args.model, i), range(args.n)):
            durations.append(ms)
            if status == 200:
                ok += 1
    p50 = sorted(durations)[len(durations) // 2] if durations else 0
    print(f"done: {ok}/{args.n} ok, p50 latency {p50:.0f} ms")
    print("Open SigNoz -> LLM Proxy dashboard to see cost / latency / tokens by model.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
