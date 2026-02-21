# Backend Status Model

> **Status in analysis table:** "Yes" — MCP Sentinel has basic connected/failed counts only.

---

## What It Is

A rich backend status model replaces simple "connected/failed" with a **multi-phase lifecycle** that accurately represents what each backend is doing at any moment.

## How ToolHive Implements It

### ToolHive Core — Phase + Conditions Model

Each backend has a **phase** (current state) and **conditions** (timestamped status messages):

| Phase | Meaning |
|-------|---------|
| `Pending` | Configured but not yet initialized |
| `Initializing` | Connection in progress, capabilities being fetched |
| `Ready` | Connected, capabilities discovered, accepting calls |
| `Degraded` | Connected but health checks report slow responses |
| `Failed` | Connection lost or initialization failed |
| `ShuttingDown` | Graceful disconnect in progress |

Conditions are a list of timestamped messages:
```json
{
  "phase": "Degraded",
  "conditions": [
    {"time": "10:30:00", "type": "HealthCheck", "status": "Warning", "message": "Response time 6200ms > 5000ms threshold"},
    {"time": "10:29:30", "type": "HealthCheck", "status": "OK", "message": "Healthy, 142ms"},
    {"time": "10:00:00", "type": "Connected", "status": "OK", "message": "Capabilities discovered: 12 tools, 3 resources"}
  ]
}
```

### ToolHive Studio — 10-State Status Model

Studio extends this with transition states for UI responsiveness:

| Status | Visual | Meaning |
|--------|--------|---------|
| `running` | 🟢 | Server is healthy and accepting calls |
| `stopped` | ⚫ | Server is not running |
| `starting` | 🟡 spinner | Server is booting up |
| `restarting` | 🟡 spinner | Server is cycling |
| `stopping` | 🟡 spinner | Graceful shutdown in progress |
| `removing` | 🟡 spinner | Being deleted |
| `updating` | 🟡 spinner | Version update in progress |
| `error` | 🔴 | Failed to start or crashed |
| `unhealthy` | 🟠 | Running but failing health checks |
| `unknown` | ⚪ | Status cannot be determined |

Studio uses **optimistic updates** — the UI immediately shows transition states (starting, stopping) before the backend confirms, then polls until the final state stabilizes.

### Aggregate Gateway Status

ToolHive derives an overall gateway status from individual backend states:
- All backends `Ready` → Gateway `Ready`
- Any backend `Degraded` → Gateway `Degraded`
- Any backend `Failed` → Gateway `PartiallyAvailable`
- All backends `Failed` → Gateway `Unavailable`

## How This Improves MCP Sentinel

### Without Rich Status
- Users see "3 connected, 1 failed" — no detail
- No visibility into initialization progress
- No distinction between "slow" and "dead"
- No lifecycle transitions visible (is it starting? stopping? stuck?)

### With Rich Status
- **TUI detail**: Each backend shows its phase with color-coding:
  ```
  ● github-server      Ready       12 tools  142ms
  ◑ database-server    Initializing  ...
  ● search-server      Degraded     8 tools  5200ms  ⚠
  ✕ broken-server      Failed       "Connection refused"
  ```
- **Transition visibility**: Users see servers cycling through phases
- **Error context**: Failed backends show the specific error
- **Aggregate display**: Footer shows overall gateway health
- **Historical conditions**: Expandable condition history per backend

## Implementation Path

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class BackendPhase(Enum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTTING_DOWN = "shutting_down"

@dataclass
class Condition:
    timestamp: datetime
    type: str
    status: str  # OK, Warning, Error
    message: str

@dataclass
class BackendStatus:
    name: str
    phase: BackendPhase = BackendPhase.PENDING
    tool_count: int = 0
    resource_count: int = 0
    last_latency_ms: float = 0
    error: str | None = None
    conditions: list[Condition] = field(default_factory=list)
    
    def transition(self, new_phase: BackendPhase, message: str = ""):
        self.phase = new_phase
        self.conditions.append(Condition(
            timestamp=datetime.now(),
            type=new_phase.value,
            status="OK" if new_phase in (BackendPhase.READY,) else "Warning",
            message=message,
        ))
```

The TUI's `BackendStatusWidget` would render this as a `DataTable` with color-coded phase column.

**Estimated effort:** Medium — the model is straightforward. The TUI rendering needs careful layout work.

**Priority:** P2 — significant UX improvement, especially when debugging backend issues.
