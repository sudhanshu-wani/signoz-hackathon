import os

# Offline mode for the whole test session: record spans, export nothing.
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")
