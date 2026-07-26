"""OpenTelemetry wiring: tracer + meter providers exporting OTLP to SigNoz.

Idempotent: calling ``setup_telemetry()`` twice is a no-op. Reads endpoint and
service name from the environment (see ``.env.example``).
"""

from __future__ import annotations

import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .attributes import (
    METRIC_GUARDRAIL_FLAG,
    METRIC_LLM_COST,
    METRIC_TASK_COST,
    METRIC_TASK_COUNT,
)

_INITIALIZED = False
_TRACER = None
_INSTRUMENTS: dict = {}

INSTRUMENTATION_NAME = "signoz-agents"


def setup_telemetry(service_name: str | None = None) -> None:
    """Configure global tracer + meter providers. Safe to call repeatedly."""
    global _INITIALIZED, _TRACER
    if _INITIALIZED:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    service = service_name or os.getenv("OTEL_SERVICE_NAME", "signoz-agents-demo")
    resource = Resource.create({"service.name": service})

    tracer_provider = TracerProvider(resource=resource)
    readers = []
    # Empty endpoint = offline mode (tests / no collector): record spans, don't
    # export. Avoids noisy connection-refused retries.
    if endpoint:
        insecure = endpoint.startswith("http://")  # gRPC insecure for localhost
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=insecure))
        )
        readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint, insecure=insecure),
                export_interval_millis=5_000,
            )
        )
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))

    _TRACER = trace.get_tracer(INSTRUMENTATION_NAME)
    _build_instruments()
    _INITIALIZED = True


def _build_instruments() -> None:
    meter = metrics.get_meter(INSTRUMENTATION_NAME)
    _INSTRUMENTS["task_cost"] = meter.create_counter(
        METRIC_TASK_COST, unit="USD", description="Task cost in USD by model/outcome"
    )
    _INSTRUMENTS["task_count"] = meter.create_counter(
        METRIC_TASK_COUNT, unit="1", description="Tasks by model/outcome"
    )
    _INSTRUMENTS["llm_cost"] = meter.create_counter(
        METRIC_LLM_COST, unit="USD", description="Per-call LLM cost in USD by model"
    )
    _INSTRUMENTS["guardrail_flag"] = meter.create_counter(
        METRIC_GUARDRAIL_FLAG, unit="1", description="Security guardrail flags"
    )


def get_tracer():
    if _TRACER is None:
        setup_telemetry()
    return _TRACER


def get_instrument(name: str):
    if not _INSTRUMENTS:
        setup_telemetry()
    return _INSTRUMENTS[name]


def force_flush(timeout_millis: int = 5_000) -> None:
    """Flush spans + metrics — call before a short-lived script exits."""
    tp = trace.get_tracer_provider()
    if hasattr(tp, "force_flush"):
        tp.force_flush(timeout_millis)
    mp = metrics.get_meter_provider()
    if hasattr(mp, "force_flush"):
        mp.force_flush(timeout_millis)
