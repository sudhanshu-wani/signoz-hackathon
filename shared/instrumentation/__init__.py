"""OpenTelemetry GenAI instrumentation core used by the proxy.

Exposes provider setup plus the canonical attribute/metric names
(`attributes.py`) so spans and dashboards can never drift apart.
"""

from .otel import force_flush, setup_telemetry

__all__ = ["setup_telemetry", "force_flush"]
