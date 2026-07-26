"""Proxy configuration from the environment."""

from __future__ import annotations

import os


def proxy_port() -> int:
    return int(os.getenv("PROXY_PORT", "8900"))


def upstream_base_url() -> str:
    # OpenAI-compatible upstream. Ollama exposes one at /v1.
    return os.getenv("UPSTREAM_BASE_URL", "http://localhost:11434/v1").rstrip("/")


def upstream_api_key() -> str:
    # Only needed for cloud upstreams (OpenAI/Anthropic-compat). Ollama needs none.
    return os.getenv("UPSTREAM_API_KEY", "")
