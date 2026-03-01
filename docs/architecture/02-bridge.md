# Bridge: Routing, Registry & Forwarding

The bridge layer connects Argus to backend MCP servers, discovers their
capabilities, and routes incoming requests to the correct backend.

## ClientManager

`argus_mcp/bridge/client_manager.py` manages the lifecycle of backend
connections.

**Responsibilities:**

- Start/stop backend MCP sessions (stdio, SSE, streamable-http)
- Track connection state per backend (6-phase lifecycle)
- Provide access to active sessions for request forwarding
- Support reconnection of individual backends

**Backend Lifecycle Phases:**

```
Pending → Initializing → Ready → Degraded → Failed
                           │                    │
                           └── ShuttingDown ◄───┘
```

| Phase | Description |
|-------|-------------|
| `Pending` | Configured but not yet started |
| `Initializing` | Connection in progress |
| `Ready` | Connected and serving capabilities |
| `Degraded` | Connected but health check failing |
| `Failed` | Connection lost or startup error |
| `ShuttingDown` | Graceful disconnect in progress |

## CapabilityRegistry

`argus_mcp/bridge/capability_registry.py` aggregates capabilities from all
connected backends.

**Process:**

1. Each backend exposes tools, resources, and prompts
2. Registry fetches capability lists from each backend session
3. Applies **filters** (allow/deny glob patterns)
4. Applies **conflict resolution** (first-wins, prefix, priority, error)
5. Applies **tool renames** (tool_overrides)
6. Builds a route map: `capability_name → backend_name`

**Route Map Example:**

```python
{
    "search_web": "browser-server",
    "read_file": "filesystem-server",
    "browser_navigate": "browser-server",  # prefix strategy
}
```

## Conflict Resolution

`argus_mcp/bridge/conflict.py` handles duplicate capability names across
backends.

| Strategy | Behavior |
|----------|----------|
| `first-wins` | First backend to register a name keeps it |
| `prefix` | Prefix with backend name: `backend_toolname` |
| `priority` | Use configured `order` list to pick the winner |
| `error` | Raise `CapabilityConflictError` at startup |

## Capability Filtering

`argus_mcp/bridge/filter.py` applies per-backend glob pattern filters:

```yaml
filters:
  tools:
    allow: ["search_*", "read_*"]
    deny: ["dangerous_*"]
```

- If `allow` is non-empty, only matching names pass
- If `deny` is non-empty, matching names are excluded
- Deny takes precedence over allow

## Tool Renaming

`argus_mcp/bridge/rename.py` applies per-backend tool overrides:

```yaml
tool_overrides:
  original_name:
    name: better_name
    description: "Improved description"
```

The original name is preserved in the route map for forwarding.

## Server Groups

`argus_mcp/bridge/groups.py` — `GroupManager` organizes backends into logical
groups:

```yaml
backends:
  server-a:
    type: stdio
    command: ...
    group: search-tools
  server-b:
    type: sse
    url: ...
    group: search-tools
```

Groups are queryable via `GET /manage/v1/groups?group=search-tools`.

## Request Forwarding

`argus_mcp/bridge/forwarder.py` is the legacy forwarding path. The modern
path uses the middleware chain's `RoutingMiddleware` which:

1. Looks up the capability in the route map
2. Resolves to the backend name
3. Gets the backend's MCP session from ClientManager
4. Calls the appropriate MCP method on the session
5. Returns the result

## Health Checking

`argus_mcp/bridge/health/` monitors backend health:

- Periodic health probes to each backend
- Maps health results to backend lifecycle phases
- Degrades gracefully — unhealthy backends are marked but not removed
- Health status visible via management API and TUI

## Tool Optimizer

`argus_mcp/bridge/optimizer/` implements the `ToolIndex`:

When large numbers of tools overwhelm LLM context windows, the optimizer
replaces the full catalog with two meta-tools:

- **`find_tool`** — Search tools by natural language query
- **`call_tool`** — Invoke a found tool by name

The `ToolIndex` maintains an in-memory index of all tools with TF-IDF-style
scoring for search relevance.

## Elicitation

`argus_mcp/bridge/elicitation.py` supports the MCP elicitation protocol,
allowing backends to request additional input from users during tool execution.

## Version Checking

`argus_mcp/bridge/version_checker.py` detects version drift between
connected backends and a tool registry, alerting when tool versions fall behind.
