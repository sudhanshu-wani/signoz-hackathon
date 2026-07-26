"""Apply the LLM Proxy dashboard + cost-spike alert to SigNoz via REST API.

    python proxy/dashboards/apply.py

Uses the direct REST API (shared/signoz_api.py). If a POST 400s, your SigNoz
version's schema differs — build the panels from panels.md in the UI.
"""

from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.signoz_api import SigNozClient  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str) -> dict:
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


def main() -> int:
    load_dotenv()
    if not os.getenv("SIGNOZ_API_KEY"):
        print("ERROR: SIGNOZ_API_KEY not set (Settings -> Service Accounts -> Keys).", file=sys.stderr)
        return 2

    client = SigNozClient()
    ok = True
    try:
        client.create_dashboard(_load("dashboard.json"))
        print("✓ dashboard created")
    except Exception as e:
        ok = False
        print(f"✗ dashboard failed: {e}\n  -> build from panels.md in the UI.")
    try:
        client.create_alert(_load("cost_spike_alert.json"))
        print("✓ cost-spike alert created")
    except Exception as e:
        ok = False
        print(f"✗ alert failed: {e}\n  -> create it in the UI (spec in cost_spike_alert.json).")
    client.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
