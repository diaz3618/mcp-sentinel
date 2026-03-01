"""Telemetry configuration.

Defines the config model and initialization for OpenTelemetry.
All OTel packages are optional — when not installed, telemetry
is silently disabled (zero overhead).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Detect optional OTel packages
try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace

    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False


@dataclass
class TelemetryConfig:
    """Configuration for OpenTelemetry integration.

    Attributes
    ----------
    enabled:
        Master switch.  When ``False``, no OTel instrumentation runs.
    otlp_endpoint:
        OTLP collector endpoint (gRPC or HTTP).
    service_name:
        Name reported to the OTel collector.
    """

    enabled: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "argus-mcp"

    def initialize(self) -> None:
        """Set up OTel TracerProvider and MeterProvider.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if not self.enabled:
            logger.debug("Telemetry disabled — skipping OTel initialization")
            return

        if not _HAS_OTEL:
            logger.warning(
                "Telemetry enabled in config but opentelemetry packages not installed. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )
            return

        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import (
                PeriodicExportingMetricReader,
            )
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import (
                BatchSpanProcessor,
            )
        except ImportError as exc:
            logger.warning("OTel SDK packages not fully installed: %s", exc)
            return

        resource = Resource.create({"service.name": self.service_name})

        # Tracing
        span_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)

        # Metrics
        metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
        reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        otel_metrics.set_meter_provider(meter_provider)

        logger.info(
            "OpenTelemetry initialized: endpoint=%s, service=%s",
            self.otlp_endpoint,
            self.service_name,
        )


def is_available() -> bool:
    """Return ``True`` if OTel packages are installed."""
    return _HAS_OTEL
