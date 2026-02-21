# Session Management

> **Status in analysis table:** "Yes" — MCP Sentinel uses stateless forwarding.

---

## What It Is

Session management tracks **per-client MCP sessions** with their own routing tables, capability snapshots, and affinity rules. Instead of all clients sharing a single global view, each session gets a consistent, isolated view of available capabilities.

## How ToolHive Implements It

### VMCPSession (`pkg/vmcp/router/`)

When a client sends `initialize`, ToolHive creates a `VMCPSession`:

```go
type VMCPSession struct {
    ID           string
    RoutingTable map[string]BackendRoute  // tool_name → backend
    Capabilities CapabilitySnapshot       // frozen list of tools/resources/prompts
    CreatedAt    time.Time
    TTL          time.Duration            // 30 minutes default
    Immutable    bool                     // true after injection
}
```

Key properties:
- **Immutable after creation**: Once the routing table is built, it doesn't change for the lifetime of the session. This prevents mid-conversation tool set changes that could confuse the LLM.
- **Session affinity**: Tool calls within a session always route to the same backend (even if conflict resolution would normally allow multiple backends for that tool name).
- **TTL-based cleanup**: Sessions expire after 30 minutes of inactivity.
- **Lazy discovery**: Capabilities are fetched from backends when the session is created, not at gateway startup. This ensures the freshest data.

### Session Headers
ToolHive uses `Mcp-Session-Id` headers (from the MCP spec) to track sessions across HTTP requests.

## How This Improves MCP Sentinel

### Without Session Management
- All clients share the same global capability list
- If a backend goes down mid-conversation, the tool disappears for all clients
- No per-client isolation — no way to give different clients different tool sets
- No affinity — consecutive tool calls might hit different backend instances

### With Session Management
- **Consistency**: The LLM sees the same tools throughout its conversation
- **Isolation**: One client's session doesn't affect another's
- **Affinity**: Backend-specific state (transactions, cursors) is preserved
- **Cleanup**: Stale sessions are automatically reclaimed
- **Foundation**: Session context enables per-session auth, rate limiting, and quotas

## Implementation Path

```python
import asyncio
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4

@dataclass
class MCPSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    routing_table: dict[str, str] = field(default_factory=dict)  # tool → backend
    created_at: float = field(default_factory=monotonic)
    last_active: float = field(default_factory=monotonic)
    ttl: float = 1800.0  # 30 minutes
    
    @property
    def expired(self) -> bool:
        return (monotonic() - self.last_active) > self.ttl
    
    def touch(self):
        self.last_active = monotonic()

class SessionManager:
    def __init__(self, capability_registry):
        self._sessions: dict[str, MCPSession] = {}
        self._registry = capability_registry
        self._cleanup_task: asyncio.Task | None = None
    
    async def create_session(self) -> MCPSession:
        session = MCPSession()
        # Snapshot current routing table
        session.routing_table = dict(self._registry.get_routing_table())
        self._sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> MCPSession | None:
        session = self._sessions.get(session_id)
        if session and not session.expired:
            session.touch()
            return session
        return None
    
    async def cleanup_loop(self):
        while True:
            expired = [sid for sid, s in self._sessions.items() if s.expired]
            for sid in expired:
                del self._sessions[sid]
            await asyncio.sleep(60)
```

### Integration with Forwarder
```python
async def forward_request(request, session_id: str | None = None):
    session = session_manager.get_session(session_id) if session_id else None
    if session:
        backend = session.routing_table.get(tool_name)
    else:
        backend = capability_registry.resolve_backend(tool_name)
    ...
```

**Estimated effort:** Medium-High — the session model is straightforward, but integrating it with the SSE transport (extracting session IDs from connections) and ensuring cleanup requires careful async lifecycle management.

**Priority:** P2 — becomes critical for multi-client deployments and when combined with health checks (sessions should survive backend reconnections).
