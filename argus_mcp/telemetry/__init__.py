"""OpenTelemetry integration — tracing, metrics, and structured logs.

All OTel dependencies are optional.  When not installed, the
telemetry subsystem is a no-op.
"""

from argus_mcp.telemetry.config import TelemetryConfig
from argus_mcp.telemetry.metrics import get_meter, record_request
from argus_mcp.telemetry.tracing import get_tracer, start_span

__all__ = [
    "TelemetryConfig",
    "get_meter",
    "get_tracer",
    "record_request",
    "start_span",
]
