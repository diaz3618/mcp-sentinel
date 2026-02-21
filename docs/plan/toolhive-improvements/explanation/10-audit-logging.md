# Audit Logging (Structured Events)

> **Status in analysis table:** "Explain" — This is an observability gap.

---

## What It Is

Audit logging records **every significant operation** as a structured JSON event. Unlike application logs (which are for debugging), audit logs answer:

- **Who** performed the action (user identity)
- **What** they did (tool call, resource read, etc.)
- **When** it happened (timestamp)
- **Where** it was routed (which backend)
- **Whether** it succeeded (outcome + error details)
- **How long** it took (latency)

## How ToolHive Implements It

ToolHive's `pkg/audit/` package implements NIST SP 800-53 compliant audit events:

### Event Structure
```json
{
  "timestamp": "2025-06-22T10:30:00Z",
  "event_type": "tool_call",
  "event_id": "uuid-v4",
  "source": {
    "user_id": "user@example.com",
    "client_ip": "10.0.0.5",
    "session_id": "mcp-session-xyz"
  },
  "target": {
    "backend": "github-server",
    "method": "tools/call",
    "tool_name": "search_issues"
  },
  "outcome": {
    "status": "success",
    "latency_ms": 142,
    "error": null
  }
}
```

### Audit Middleware
The audit middleware wraps every MCP request:
1. Captures request metadata (user, method, tool name, backend)
2. Forwards to next middleware
3. Captures response metadata (status, latency, error)
4. Emits the structured audit event

### Workflow Auditor
For composite workflows, a dedicated auditor tracks the entire DAG execution with per-step audit records.

### Custom Log Level
ToolHive defines a custom `LevelAudit` log level that's always enabled (cannot be suppressed by normal log level configuration). This ensures audit events are never accidentally silenced.

## How This Improves MCP Sentinel

### Without Audit Logging
- No record of which tools were called or by whom
- Cannot investigate incidents ("who deleted the production data?")
- No compliance evidence for security audits
- Cannot measure tool usage patterns or backend performance

### With Audit Logging
- Complete operation trail for forensic analysis
- Compliance evidence (SOC 2, ISO 27001, NIST)
- Usage analytics: most-called tools, slowest backends, error rates
- Alerting foundation: trigger alerts on specific event patterns
- TUI integration: display real-time audit events in the event log widget

## Implementation Path for MCP Sentinel

### Phase 1: Structured Logging with `structlog`

```python
import structlog

audit_logger = structlog.get_logger("mcp_sentinel.audit")

async def audit_middleware(request: MCPRequest, next_handler):
    start = time.monotonic()
    try:
        result = await next_handler(request)
        audit_logger.info(
            "mcp_operation",
            event_type=request.method,
            backend=request.target_backend,
            tool_name=request.params.get("name"),
            outcome="success",
            latency_ms=round((time.monotonic() - start) * 1000),
        )
        return result
    except Exception as e:
        audit_logger.error(
            "mcp_operation",
            event_type=request.method,
            backend=request.target_backend,
            tool_name=request.params.get("name"),
            outcome="error",
            error=str(e),
            latency_ms=round((time.monotonic() - start) * 1000),
        )
        raise
```

### Phase 2: Dedicated Audit Log File

```json
{
  "audit": {
    "enabled": true,
    "file": "logs/audit.jsonl",
    "rotation": {
      "max_size_mb": 100,
      "backup_count": 5
    }
  }
}
```

### Phase 3: TUI Integration
Display audit events in real-time in the EventLogWidget, with filtering by event type, backend, and outcome.

**Estimated effort:** Medium. `structlog` does most of the heavy lifting. The main work is threading the audit call through the forwarding layer.

**Priority:** P1 — high value for any deployment.
