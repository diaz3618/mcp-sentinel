# Health Checks & Circuit Breaker

> **Status in analysis table:** "Yes" — MCP Sentinel has no health monitoring.

---

## What It Is

Health checks periodically probe each backend MCP server to determine if it's alive, degraded, or dead. Combined with a **circuit breaker**, MCP Sentinel can automatically stop routing to failing backends and resume when they recover.

## How ToolHive Implements It

### Health Monitor (`pkg/vmcp/health/`)

- **Probe mechanism**: Sends MCP `ping` (or `ListCapabilities` as a fallback) to each backend
- **Check interval**: Every 30 seconds (configurable)
- **Per-backend goroutines**: Each backend has its own health check goroutine
- **Startup gate**: `initialCheckWg` ensures all backends are checked once before the gateway accepts traffic

### Health States

| State | Meaning | Tool Advertising |
|-------|---------|-----------------|
| `healthy` | Backend responds within threshold | Tools advertised normally |
| `degraded` | Backend responds but slowly (>5s) | Tools still advertised, warning logged |
| `unhealthy` | Backend fails to respond | Tools can be hidden from `tools/list` |
| `unknown` | Never checked or check in progress | Treated as healthy (optimistic) |

### Circuit Breaker Pattern
```
CLOSED → (N consecutive failures) → OPEN → (cooldown period) → HALF-OPEN → (probe succeeds) → CLOSED
                                                                         → (probe fails) → OPEN
```

- **Closed**: Normal operation, requests flow through
- **Open**: Backend is down. Requests immediately fail without attempting connection. Tools optionally hidden.
- **Half-Open**: After cooldown, one probe request is sent. If it succeeds, circuit closes. If it fails, circuit re-opens.

Parameters:
- `failureThreshold`: Number of consecutive failures to trip the breaker (default: 3)
- `degradedThreshold`: Response time above which backend is "degraded" (default: 5s)
- `cooldownPeriod`: Time to wait before probing an open circuit (default: 60s)

## How This Improves MCP Sentinel

### Without Health Checks
- MCP Sentinel doesn't know if a backend is down until a tool call fails
- Failed tool calls return errors to the LLM, wasting tokens and conversation context
- Dead backends still appear in `tools/list`, confusing the LLM
- No automatic recovery detection — manual restart required

### With Health Checks
- **Proactive detection**: Dead backends detected within 30 seconds
- **Graceful degradation**: Unhealthy backends' tools hidden from `tools/list`
- **Automatic recovery**: When backend comes back, circuit closes, tools re-appear
- **TUI visibility**: Health status shown in `BackendStatusWidget` with color coding
- **Performance**: Circuit breaker prevents wasting time on known-dead backends

## Implementation Path for MCP Sentinel

```python
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from time import monotonic

class HealthState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

@dataclass
class BackendHealth:
    state: HealthState = HealthState.UNKNOWN
    circuit: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_check: float = 0
    last_latency_ms: float = 0
    last_error: str | None = None

class HealthMonitor:
    def __init__(self, client_manager, interval: float = 30.0):
        self._cm = client_manager
        self._interval = interval
        self._health: dict[str, BackendHealth] = {}
        self._task: asyncio.Task | None = None
    
    async def start(self):
        self._task = asyncio.create_task(self._run())
    
    async def _run(self):
        while True:
            await asyncio.gather(
                *(self._check(name) for name in self._cm.backends),
                return_exceptions=True,
            )
            await asyncio.sleep(self._interval)
    
    async def _check(self, name: str):
        health = self._health.setdefault(name, BackendHealth())
        start = monotonic()
        try:
            await asyncio.wait_for(
                self._cm.ping(name), timeout=10.0
            )
            latency = (monotonic() - start) * 1000
            health.last_latency_ms = latency
            health.consecutive_failures = 0
            health.state = (
                HealthState.DEGRADED if latency > 5000
                else HealthState.HEALTHY
            )
            health.circuit = CircuitState.CLOSED
        except Exception as e:
            health.consecutive_failures += 1
            health.last_error = str(e)
            if health.consecutive_failures >= 3:
                health.state = HealthState.UNHEALTHY
                health.circuit = CircuitState.OPEN
```

**Estimated effort:** Medium — the asyncio health loop is straightforward. Circuit breaker logic requires careful state management.

**Priority:** P1 — fundamental for any deployment with more than one backend.
