#!/usr/bin/env bash
# Keep the demo dashboard's last-30m window populated: a small burst of real
# mixed-model requests (with a pinch of real failure injection) every ~2 min.
# Kill with Ctrl-C when done recording/screenshotting.
cd "$(dirname "$0")/.."
while true; do
  .venv/bin/python scripts/generate_traffic.py --n 6 --concurrency 2 --mix --chaos 0.1 | tail -1
  sleep 120
done
