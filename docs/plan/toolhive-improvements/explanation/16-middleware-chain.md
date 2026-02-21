# Middleware Chain Architecture

> **Status in analysis table:** "Yes" — MCP Sentinel does direct forwarding with no middleware.

---

## What It Is

A middleware chain is a **composable request processing pipeline** where each middleware wraps the next handler. Each layer can inspect, modify, or reject requests before they reach the backend, and inspect/modify responses on the way back.

Think of it like Russian nesting dolls — each middleware wraps the next one:

```
Client Request
  → Recovery (catch panics)
    → Header Validation
      → Authentication
        → Authorization
          → Audit Logger
            → Telemetry
              → Tool Filter
                → Backend Router
                  → Backend Call
                ← Response
              ← Record metrics
            ← Log audit event
          ← Check passed
        ← User verified
      ← Headers OK
    ← Error caught
  ← Response to client
```

## How ToolHive Implements It

ToolHive's `pkg/transport/middleware/` package chains **11 middleware types**:

1. **Recovery** — Catches panics/errors, returns clean error response
2. **Header Validation** — Validates required MCP headers
3. **Authentication** — Validates JWT/OIDC tokens
4. **Authorization** — Cedar policy evaluation
5. **Audit** — Records structured audit events
6. **Discovery** — Handles `tools/list`, `resources/list` responses
7. **Backend Enrichment** — Adds backend metadata to context
8. **MCP Parsing** — Parses JSON-RPC messages
9. **Telemetry** — OpenTelemetry span creation + metrics
10. **Tool Filter** — Applies allow/deny lists
11. **Tool Call Filter** — Validates tool call arguments

Each middleware implements a simple interface:
```go
type Middleware func(next http.Handler) http.Handler
```

Chain construction:
```go
chain := middleware.Chain(
    middleware.Recovery(),
    middleware.Auth(authenticator),
    middleware.Audit(auditLogger),
    middleware.Telemetry(tracer),
    // ... more middleware
)(finalHandler)
```

## How This Improves MCP Sentinel

### Without Middleware
- All request processing logic lives in the forwarder function
- Adding new cross-cutting concerns (auth, audit, metrics) requires modifying the forwarder
- No way to opt-in/out of processing steps per deployment
- Testing individual concerns in isolation is difficult
- Code grows into a monolithic function

### With Middleware
- **Separation of concerns**: Each middleware handles one responsibility
- **Composable**: Enable/disable middleware via config (don't need auth? don't add it to the chain)
- **Testable**: Each middleware can be unit-tested independently
- **Extensible**: Adding new functionality = writing a new middleware class
- **Ordered**: The chain order determines execution semantics (auth before authz, etc.)

## Implementation Path for MCP Sentinel

### Protocol Definition

```python
from typing import Callable, Awaitable, Any

# MCP request/response types
MCPRequest = dict[str, Any]
MCPResponse = dict[str, Any]
MCPHandler = Callable[[MCPRequest], Awaitable[MCPResponse]]
MCPMiddleware = Callable[[MCPRequest, MCPHandler], Awaitable[MCPResponse]]
```

### Chain Builder

```python
def build_chain(middlewares: list[MCPMiddleware], handler: MCPHandler) -> MCPHandler:
    """Build a middleware chain wrapping the final handler."""
    chain = handler
    for mw in reversed(middlewares):
        next_handler = chain
        chain = lambda req, _mw=mw, _next=next_handler: _mw(req, _next)
    return chain
```

### Example Middleware

```python
async def recovery_middleware(request: MCPRequest, next_handler: MCPHandler) -> MCPResponse:
    """Catch exceptions and return clean MCP error responses."""
    try:
        return await next_handler(request)
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request.get("id"),
        }

async def logging_middleware(request: MCPRequest, next_handler: MCPHandler) -> MCPResponse:
    """Log every MCP request and response."""
    logger.info("MCP request", method=request.get("method"), id=request.get("id"))
    start = time.monotonic()
    response = await next_handler(request)
    elapsed = (time.monotonic() - start) * 1000
    logger.info("MCP response", id=request.get("id"), elapsed_ms=elapsed)
    return response
```

### Config-Driven Chain

```json
{
  "middleware": {
    "chain": ["recovery", "logging", "audit", "tool_filter"],
    "audit": { "file": "logs/audit.jsonl" },
    "tool_filter": { "mode": "allow", "names": ["..."] }
  }
}
```

**Estimated effort:** Medium — the chain pattern is simple. The effort is in writing individual middleware implementations.

**Priority:** P1 — this is an architectural foundation that other features (auth, audit, telemetry) build on. Implement this before adding individual middleware.
