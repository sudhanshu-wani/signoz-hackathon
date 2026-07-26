"""Thin SigNoz REST client (direct API — deliberately NOT the MCP server).

We use the REST API, not the MCP server, on purpose: MCP loads many verbose tool
schemas into an LLM's context and returns fat JSON, which burns tokens at
runtime. The direct API lets us expose exactly the calls we need and trim
responses ourselves.

Auth: ``SIGNOZ-API-KEY`` header (key from Settings -> Service Accounts -> Keys).

IMPORTANT — version sensitivity: the ``/api/v5/query_range`` request body has
changed across SigNoz releases. The query builders here are quarantined in
``query_task_metrics`` / ``fetch_recent_task_spans`` and marked so; validate the
body against YOUR SigNoz version (paste a working query from the UI's "view
API" / network tab if it differs). The dashboard + alert calls are stable.
"""

from __future__ import annotations

import os

import httpx


class SigNozClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = 30.0):
        self.base_url = (base_url or os.getenv("SIGNOZ_API_URL", "http://localhost:8080")).rstrip("/")
        self.api_key = api_key or os.getenv("SIGNOZ_API_KEY", "")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"SIGNOZ-API-KEY": self.api_key, "Content-Type": "application/json"},
        )

    # --- generic ---
    def post(self, path: str, json: dict) -> dict:
        r = self._client.post(path, json=json)
        r.raise_for_status()
        return r.json() if r.content else {}

    def get(self, path: str) -> dict:
        r = self._client.get(path)
        r.raise_for_status()
        return r.json() if r.content else {}

    def close(self) -> None:
        self._client.close()

    # --- dashboards (stable: /api/v2/dashboards) ---
    def create_dashboard(self, dashboard_json: dict) -> dict:
        """Create a dashboard from an exported dashboard JSON body."""
        return self.post("/api/v2/dashboards", {"data": dashboard_json})

    # --- alerts (stable: /api/v1/rules) ---
    def create_alert(self, rule_json: dict) -> dict:
        return self.post("/api/v1/rules", rule_json)

    # --- querying (VERSION-SENSITIVE: verify body against your build) ---
    def raw_query_range(self, body: dict) -> dict:
        """Passthrough to POST /api/v5/query_range. Body shape is your build's."""
        return self.post("/api/v5/query_range", body)
