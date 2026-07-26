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
    """Auth, in order of preference:
    1. SIGNOZ_API_KEY  -> `SIGNOZ-API-KEY` header (Settings -> API keys).
    2. SIGNOZ_EMAIL + SIGNOZ_PASSWORD -> login flow (org discovered via
       /api/v2/sessions/context, JWT via /api/v2/sessions/email_password).
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = 30.0):
        self.base_url = (base_url or os.getenv("SIGNOZ_API_URL", "http://localhost:8080")).rstrip("/")
        self.api_key = api_key or os.getenv("SIGNOZ_API_KEY", "")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["SIGNOZ-API-KEY"] = self.api_key
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout, headers=headers)
        if not self.api_key:
            email = os.getenv("SIGNOZ_EMAIL", "")
            password = os.getenv("SIGNOZ_PASSWORD", "")
            if email and password:
                self._login(email, password)

    def _login(self, email: str, password: str) -> None:
        ctx = self._client.get(f"/api/v2/sessions/context?email={email}")
        ctx.raise_for_status()
        orgs = ctx.json()["data"]["orgs"]
        r = self._client.post(
            "/api/v2/sessions/email_password",
            json={"email": email, "password": password, "orgID": orgs[0]["id"]},
        )
        r.raise_for_status()
        token = r.json()["data"]["accessToken"]
        self._client.headers["Authorization"] = f"Bearer {token}"

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

    # --- dashboards (verified on v0.134: POST /api/v1/dashboards, raw body) ---
    def create_dashboard(self, dashboard_json: dict) -> dict:
        """Create a dashboard from an exported dashboard JSON body."""
        return self.post("/api/v1/dashboards", dashboard_json)

    # --- alerts (stable: /api/v1/rules) ---
    def create_alert(self, rule_json: dict) -> dict:
        return self.post("/api/v1/rules", rule_json)

    # --- querying (VERSION-SENSITIVE: verify body against your build) ---
    def raw_query_range(self, body: dict) -> dict:
        """Passthrough to POST /api/v5/query_range. Body shape is your build's."""
        return self.post("/api/v5/query_range", body)
