# OpenTelemetry Integration

> **Status in analysis table:** "Explain" — This is an observability gap.

---

## What It Is

OpenTelemetry (OTel) is the industry-standard framework for **distributed tracing, metrics, and logs**. It lets you:

- **Trace** a request's journey through MCP Sentinel → backend → response
- **Measure** latency, error rates, and throughput per backend and per tool
- **Export** telemetry data to any observability platform (Jaeger, Datadog, Grafana, New Relic, etc.)

## How ToolHive Implements It

ToolHive's `pkg/telemetry/` package provides full-stack observability:

### Tracing
- Every MCP request creates a distributed trace span
- Child spans for: middleware processing, backend routing, backend call, response parsing
- Trace context propagated to backends via `traceparent` headers
- Exporters: OTLP (gRPC/HTTP), Jaeger, stdout

### Metrics (Prometheus)
ToolHive exposes a `/metrics` endpoint with:

| Metric | Type | Labels |
|--------|------|--------|
| `mcp_requests_total` | Counter | method, backend, status |
| `mcp_request_duration_seconds` | Histogram | method, backend |
| `mcp_tool_calls_total` | Counter | tool_name, backend, status |
| `mcp_active_sessions` | Gauge | — |
| `mcp_backend_health` | Gauge | backend, status |

### Telemetry Middleware
Positioned in the middleware chain after auth and before MCP parsing:
1. Creates a trace span for the request
2. Records start time
3. Forwards to next middleware
4. Records duration and status
5. Increments counters

## How This Improves MCP Sentinel

### Without OpenTelemetry
- No visibility into request flow or latency breakdown
- Cannot identify slow backends or failing tools
- No way to correlate MCP Sentinel events with upstream/downstream systems
- Manual debugging of performance issues

### With OpenTelemetry
- **Request tracing**: See the full lifecycle of every MCP call — from client to backend and back
- **Performance dashboards**: Grafana dashboards showing p50/p95/p99 latency per backend
- **Error tracking**: Automatic error rate alerting per tool or backend
- **Capacity planning**: Understanding throughput limits and bottlenecks
- **Integration**: Same traces flow into existing observability stack (Datadog, Grafana Cloud, etc.)

## Implementation Path for MCP Sentinel

### Phase 1: Tracing with OTLP

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup (once at startup)
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("mcp_sentinel")

# Usage in forwarder
async def forward_request(backend: str, method: str, params: dict):
    with tracer.start_as_current_span(
        f"mcp.{method}",
        attributes={
            "mcp.backend": backend,
            "mcp.method": method,
            "mcp.tool": params.get("name", ""),
        },
    ) as span:
        try:
            result = await backend_client.call(method, params)
            span.set_status(StatusCode.OK)
            return result
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise
```

### Phase 2: Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

mcp_requests = Counter("mcp_requests_total", "Total MCP requests", ["method", "backend", "status"])
mcp_duration = Histogram("mcp_request_duration_seconds", "Request duration", ["method", "backend"])
mcp_backends_up = Gauge("mcp_backend_health", "Backend health status", ["backend"])
```

### Config Example

```json
{
  "telemetry": {
    "tracing": {
      "enabled": true,
      "exporter": "otlp",
      "endpoint": "http://localhost:4317"
    },
    "metrics": {
      "enabled": true,
      "prometheus_port": 9090
    }
  }
}
```

### Dependencies
- `opentelemetry-api`, `opentelemetry-sdk`
- `opentelemetry-exporter-otlp` (for trace export)
- `prometheus-client` (for `/metrics` endpoint)

**Estimated effort:** High. The instrumentation itself is straightforward, but proper span propagation, metric cardinality control, and configuration require careful design.

**Priority:** P3 — most valuable for production multi-user deployments. Single-user TUI deployments get limited benefit.
