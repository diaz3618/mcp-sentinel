# ToolHive Platform Analysis — Features Portable to MCP-Gateway

> Phase 5 Research Output — Analysis of the ToolHive ecosystem  
> Date: 2025-06-22  
> Repos inspected: `toolhive` (Go), `toolhive-cloud-ui` (Next.js), `toolhive-studio` (Electron)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Repos Inspected](#repos-inspected)
3. [Current MCP-Gateway vs ToolHive](#current-mcp-gateway-vs-toolhive)
4. [Priority Matrix — Portable Features](#priority-matrix--portable-features)
5. [P0 — Quick Wins (Low Effort, High Impact)](#p0--quick-wins)
6. [P1 — Core Enhancements (Medium Effort, High Impact)](#p1--core-enhancements)
7. [P2 — Advanced Features (Medium-High Effort)](#p2--advanced-features)
8. [P3 — Future Considerations](#p3--future-considerations)
9. [Non-Portable Features](#non-portable-features)
10. [TUI Enhancement Ideas (from Cloud UI & Studio)](#tui-enhancement-ideas)
11. [Existing Code Touchpoints](#existing-code-touchpoints)

---

## Executive Summary

ToolHive is a **platform for securely managing, proxying, deploying, and aggregating MCP servers**. Written in Go, it ships as:

- **`thv` CLI** — Container-based MCP server lifecycle management
- **Virtual MCP Server (`vmcp`)** — Gateway/aggregator merging multiple backends into one MCP endpoint
- **K8s Operator** — CRD-based management at scale
- **Cloud UI** — Next.js registry browser + AI chat playground  
- **Studio** — Electron desktop app for local server management

ToolHive's `vmcp` component is the closest analog to MCP-Gateway. Both aggregate multiple MCP backend servers behind a single endpoint. However, ToolHive's vmcp is **significantly more mature** in middleware, security, observability, and conflict resolution.

MCP-Gateway has **one clear advantage**: the Textual TUI for real-time monitoring, which no ToolHive component provides.

This document identifies **17 portable features** organized by priority, with implementation guidance for each.

---

## Repos Inspected

### `repos/toolhive/` — Core Platform (Go)
- **79 packages** across `cmd/` and `pkg/`
- Four binaries: `thv`, `thv-operator`, `thv-proxyrunner`, `vmcp`
- Key packages: `pkg/vmcp/` (aggregator), `pkg/transport/` (proxy), `pkg/auth/`, `pkg/authz/`, `pkg/audit/`, `pkg/telemetry/`
- Design patterns: Factory, Middleware Chain, Interface Segregation, DDD (vmcp), DAG-based workflow execution

### `repos/toolhive-cloud-ui/` — Web Dashboard (Next.js 16)
- Next.js App Router + React 19 + TypeScript + Tailwind + shadcn/ui
- Auto-generated API client from OpenAPI spec
- Features: MCP server catalog, AI chat playground with MCP tool integration, registry browser
- MCP transports: SSE + StreamableHTTP via `@modelcontextprotocol/sdk`

### `repos/toolhive-studio/` — Desktop App (Electron 40)
- Electron Forge + Vite + React 19 + TanStack Router/Query
- Three-process model: Main (server management) → Preload (IPC bridge) → Renderer (UI)
- Features: Server lifecycle management, polling-based status, feature flags, secrets management, AI chat playground
- ~80+ IPC channels, composable polling engine, graceful shutdown with server tracking

---

## Current MCP-Gateway vs ToolHive

| Area | ToolHive (`vmcp`) | MCP-Gateway | Status |
|------|-------------------|-------------|--------|
| Backend: stdio | ✅ (container stdio + proxy) | ✅ (subprocess stdio via `mcp` SDK) | **Parity** |
| Backend: SSE | ✅ (transparent proxy) | ✅ (via `sse_client`) | **Parity** |
| Backend: streamable-http | ✅ (transparent proxy) | ❌ | **Gap** |
| Capability aggregation | ✅ (tools, resources, prompts) | ✅ (tools, resources, prompts) | **Parity** |
| Conflict resolution | 3 strategies: prefix, priority, manual | First-wins only (duplicate ignored + warning) | **Gap** |
| Tool filtering | Allow/deny lists per backend | None | **Gap** |
| Tool renaming | Per-tool rename + description override | None | **Gap** |
| Composite workflows | DAG-based multi-step with elicitation | None | **Gap** |
| Optimizer (find_tool/call_tool) | Semantic search, token savings metrics | None | **Gap** |
| Incoming auth | OIDC/OAuth2, anonymous, local JWT | None | **Gap** |
| Outgoing auth | Token exchange, header injection | None | **Gap** |
| Authorization | Cedar policies, HTTP-based PDP | None | **Gap** |
| Audit logging | NIST SP 800-53 compliant events | None | **Gap** |
| OpenTelemetry tracing | Full OTLP + Jaeger + DataDog | None | **Gap** |
| Prometheus metrics | `/metrics` endpoint | None | **Gap** |
| Health checks | MCP ping protocol, circuit breaker | None | **Gap** |
| Session management | Per-session routing tables, affinity | Stateless forwarding | **Gap** |
| Secret management | Encrypted AES-256-GCM, 1Password, env | Plaintext in config.json | **Gap** |
| Config format | YAML with full schema, versioned | JSON with minimal validation | **Gap** |
| Config export/import | RunConfig portable format | No | **Gap** |
| Server groups | Logical collections | No | **Gap** |
| Registry | Curated catalog with provenance | No | **Gap** |
| Client auto-config | Claude Desktop, Cursor, VS Code | No | **Gap** |
| TUI monitoring | No (CLI-only) | ✅ (Textual TUI) | **Advantage** |
| Middleware chain | 11 composable middleware types | Direct forwarding | **Gap** |
| Backend status model | Phase, conditions, health status | Basic connected/failed count | **Gap** |

---

## Priority Matrix — Portable Features

| Priority | Feature | Impact | Effort | Existing Touchpoint |
|----------|---------|--------|--------|---------------------|
| **P0** | Conflict resolution strategies | High | Low | `capability_registry.py` L42 TODO |
| **P0** | Tool filtering (allow/deny) | High | Low | `capability_registry.py` |
| **P0** | Configurable timeouts | Medium | Low | `constants.py` hardcoded values |
| **P1** | Health checks (MCP ping + status) | High | Medium | `client_manager.py` |
| **P1** | Tool renaming / description override | Medium | Low | `capability_registry.py` |
| **P1** | Audit logging (structured JSON) | High | Medium | `display/logging_config.py` |
| **P1** | Middleware chain architecture | High | Medium | `bridge/forwarder.py` |
| **P2** | Optimizer (find_tool / call_tool) | High | Medium | New module |
| **P2** | Outgoing auth (header injection) | High | Medium | `config/loader.py` |
| **P2** | Backend status model | Medium | Medium | `tui/` widgets |
| **P2** | Session-aware routing | Medium | Medium-High | `server/app.py` |
| **P2** | Server groups | Medium | Low | `config.json` |
| **P3** | OpenTelemetry integration | High | High | New module |
| **P3** | Incoming authentication (JWT) | High | High | Starlette middleware |
| **P3** | Composite tool workflows | High | High | New module |
| **P3** | Streamable HTTP transport | Medium | Medium | `client_manager.py` |
| **P3** | Secret management | Medium | Medium | `config/loader.py` |

---

## P0 — Quick Wins

### 1. Conflict Resolution Strategies

**What**: Instead of silently ignoring duplicate capability names, offer configurable strategies.

**ToolHive implementation** (`pkg/vmcp/aggregator/`):
- **Prefix strategy**: Auto-prefix with backend name → `{backend}_toolname`
- **Priority strategy**: Configurable backend ordering, first wins
- **Manual mapping**: Explicit name→backend mappings in config

**MCP-Gateway touchpoint**: `mcp_gateway/bridge/capability_registry.py` line 42 already has:
```python
# TODO: Make conflict resolution strategy configurable
# (for example, auto-prefixing).
```

**Config addition** (`config.json`):
```json
{
  "conflict_resolution": {
    "strategy": "prefix",
    "separator": "_"
  }
}
```

Strategies: `"first_wins"` (current behavior), `"prefix"` (auto-prefix with server name), `"error"` (fail on conflicts).

---

### 2. Tool Filtering (Allow/Deny per Backend)

**What**: Per-server allow/deny lists to control which tools are exposed.

**ToolHive implementation** (`pkg/vmcp/aggregator/`):
- `allowList` / `denyList` per workload
- Applied during capability discovery before aggregation

**MCP-Gateway implementation**: Add per-server config:
```json
{
  "mcpServers": {
    "my-server": {
      "url": "...",
      "tools_filter": {
        "mode": "allow",
        "names": ["tool_a", "tool_b"]
      }
    }
  }
}
```

**Touchpoint**: Filter in `_discover_caps_by_type()` after parsing capabilities, before adding to `agg_list`.

---

### 3. Configurable Timeouts

**What**: Per-backend and per-operation timeout configuration instead of hardcoded constants.

**Current hardcoded values** (`mcp_gateway/constants.py`):
```python
SSE_LOCAL_START_DELAY = 5
MCP_INIT_TIMEOUT = 15
CAP_FETCH_TIMEOUT = 10.0
```

**Config addition**:
```json
{
  "timeouts": {
    "sse_start_delay": 5,
    "mcp_init": 15,
    "capability_fetch": 10,
    "tool_call": 30
  },
  "mcpServers": {
    "slow-server": {
      "timeouts": {
        "capability_fetch": 30,
        "tool_call": 120
      }
    }
  }
}
```

**Touchpoint**: `config/loader.py` parses timeouts; `bridge/` modules read from config instead of constants.

---

## P1 — Core Enhancements

### 4. Health Checks (MCP Ping + Status)

**What**: Periodic MCP `ping` to each backend with status tracking.

**ToolHive implementation** (`pkg/vmcp/health/`):
- Health monitor with configurable interval
- States: `healthy`, `degraded`, `unhealthy`
- Circuit breaker: after N failures, stop listing tools from that backend
- Health status in API responses

**ToolHive Studio pattern**: Composable polling engine with `pollServerStatus`, `pollServerUntilStable` — transition state detection with auto-resume polling.

**MCP-Gateway implementation**:
- Background `asyncio.Task` pinging backends every N seconds
- Per-backend status: `healthy | degraded | unhealthy | unknown`
- Display in TUI's `BackendStatus` widget (already exists)
- Optional: exclude unhealthy backends from `list_tools` responses

---

### 5. Tool Renaming / Description Override

**What**: Per-tool name aliasing and description customization.

**ToolHive implementation** (`pkg/vmcp/aggregator/`):
- `renames` map: `{original_name: new_name}`
- `description_overrides` map: `{tool_name: "custom description"}`

**Config addition**:
```json
{
  "mcpServers": {
    "my-server": {
      "tool_overrides": {
        "original_tool_name": {
          "name": "better_name",
          "description": "A clearer description of what this does"
        }
      }
    }
  }
}
```

**Touchpoint**: Apply in `_discover_caps_by_type()` after parsing, before conflict detection.

---

### 6. Audit Logging (Structured JSON Events)

**What**: Structured JSON log events for every MCP operation.

**ToolHive implementation** (`pkg/audit/`):
- NIST SP 800-53 compliant event structure
- Fields: timestamp, event_type, source, target_backend, method, tool_name, outcome, latency_ms, error
- Middleware-based collection
- Optional file output + log rotation

**MCP-Gateway implementation**:
- Python `logging` with JSON formatter (or `structlog`)
- Log at the forwarding layer (`bridge/forwarder.py`)
- Structured fields via `extra` dict
- Separate audit log file configurable in `config.json`

---

### 7. Middleware Chain Architecture

**What**: Composable request processing pipeline for the proxy layer.

**ToolHive implementation** (`pkg/transport/middleware/`):
- 11 middleware types: auth, authz, audit, telemetry, recovery, tool filter, tool call filter, usage metrics, parser, header forwarding, backend enrichment
- Chain pattern: each middleware wraps the next handler

**MCP-Gateway implementation**:
- Python async middleware chain wrapping `forward_request()`
- Starlette already supports middleware natively for HTTP layer
- MCP-level middleware for tool call processing:

```python
# Middleware protocol
class MCPMiddleware(Protocol):
    async def __call__(self, request: MCPRequest, next: Callable) -> MCPResponse: ...

# Chain execution
async def execute_chain(middlewares: list, request, handler):
    if not middlewares:
        return await handler(request)
    return await middlewares[0](request, lambda r: execute_chain(middlewares[1:], r, handler))
```

**Starting set**: Recovery (exception catch), Logging/Audit, Request Validation.

---

## P2 — Advanced Features

### 8. Optimizer (find_tool / call_tool Meta-Tools)

**What**: Instead of exposing 100+ tools to the LLM, expose two meta-tools.

**ToolHive implementation** (`pkg/vmcp/optimizer/`):
- `find_tool`: Semantic search over tool names + descriptions, returns top-N matches
- `call_tool`: Dynamic invocation by name, forwards to correct backend
- SQLite-backed tool store for search
- Token usage metrics: baseline vs returned token savings

**MCP-Gateway implementation**:
- In-memory tool index (name + description searchable)
- `find_tool(query, limit)` → returns matching tool definitions
- `call_tool(name, args)` → resolves backend + forwards
- Toggle in config: `"optimizer": { "enabled": true, "max_results": 10 }`

---

### 9. Outgoing Auth (Header Injection)

**What**: Inject auth headers when calling backend servers.

**ToolHive implementation** (`pkg/vmcp/auth/`):
- Two-boundary auth: incoming client validation + outgoing backend credentials
- Per-backend header injection (`Authorization: Bearer <token>`)
- Token exchange (RFC 8693)
- Token caching (memory, Redis)

**MCP-Gateway implementation** (simplified):
```json
{
  "mcpServers": {
    "protected-server": {
      "url": "https://api.example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer $API_TOKEN"
      }
    }
  }
}
```

- `$ENV_VAR` syntax for env var expansion
- Headers injected during SSE client connection

---

### 10. Backend Status Model

**What**: Rich status model beyond connected/failed counts.

**ToolHive implementation** (`pkg/vmcp/status/`):
- Phases: `Pending`, `Initializing`, `Ready`, `Degraded`, `Failed`, `ShuttingDown`
- Conditions: timestamped status messages per backend
- Aggregate gateway status derived from backend states

**ToolHive Studio pattern**: Server cards with color-coded status badges (🟢 running, 🔴 stopped, 🟡 transition) + polling-based status updates.

**MCP-Gateway implementation**:
- `BackendStatus` dataclass with phase, last_seen, error_count, latency_ms
- Update from health checks
- Display rich status in TUI (color-coded, phase + conditions)

---

### 11. Session-Aware Routing

**What**: Per-MCP-session capability tables.

**ToolHive implementation** (`pkg/vmcp/router/`):
- Per-session routing tables created on `initialize`
- Session affinity: tool calls routed to same backend within session
- Lazy discovery: capabilities fetched on first use per session

---

### 12. Server Groups

**What**: Logical grouping of backend servers.

**ToolHive implementation** (`pkg/groups/`):
- Named groups (e.g., "development", "production")
- Multiple vmcp endpoints serving different groups
- Group-level operations (start/stop all in group)

**ToolHive Studio pattern**: Server groups in the sidebar, group-based filtering.

**Config addition**:
```json
{
  "groups": {
    "dev": ["server-a", "server-b"],
    "prod": ["server-c"]
  }
}
```

---

## P3 — Future Considerations

### 13. OpenTelemetry Integration
- Python `opentelemetry-api` + `opentelemetry-sdk`
- Instrument `forward_request()` with spans
- OTLP exporter for traces, optional Prometheus for metrics

### 14. Incoming Authentication (JWT/OIDC)
- Starlette middleware validating JWT on SSE connections
- API key or Bearer token validation
- OIDC discovery for public key retrieval

### 15. Composite Tool Workflows
- YAML workflow definitions with DAG-based execution
- Steps reference tools from different backends
- Conditional execution + template expansion
- `asyncio.gather()` for parallel steps

### 16. Streamable HTTP Transport
- Support the new MCP streamable-http transport for backends
- Add alongside `stdio` and `sse` in `ClientManager`
- SSE is being deprecated in the MCP spec

### 17. Secret Management
- `$ENV_VAR` syntax in config values (replace at load time)
- Optional encrypted secrets file
- `cryptography` library for AES-256-GCM
- Avoid plaintext API keys in `config.json`

---

## Non-Portable Features

These ToolHive features are tied to Go/container/K8s architecture and do **not** apply:

| Feature | Reason |
|---------|--------|
| Container runtime abstraction (Docker/Podman/Colima) | MCP-Gateway uses subprocess stdio, not containers |
| Protocol scheme auto-containerization (`uvx://`, `npx://`) | Container-specific |
| Kubernetes Operator + CRDs | K8s-native, not relevant for Python process |
| Proxy Runner (thv-proxyrunner) | K8s sidecar pattern |
| Container permission profiles | Container security model |
| Image certificate/provenance validation | Container supply chain |
| Cedar policy language | Limited Python ecosystem support |
| Cobra CLI framework | Go-specific |
| OS keyring integration | Platform-specific, different scope |
| Electron IPC patterns | Desktop app architecture |
| Deep linking (toolhive-gui://) | OS protocol registration |
| Auto-update (Squirrel) | Desktop app distribution |
| System tray integration | Desktop-only |

---

## TUI Enhancement Ideas (from Cloud UI & Studio)

The Cloud UI and Studio provide excellent UX patterns that could enhance MCP-Gateway's Textual TUI:

### From Cloud UI
| Pattern | TUI Adaptation |
|---------|----------------|
| Grid ↔ List view toggle | Compact (1-line per server) vs. expanded (multi-line detail) view |
| Server search/filter bar | `Input` widget for real-time filtering of server list |
| Server detail with tabs (About / Tools) | `TabbedContent` with server info + tools table |
| Per-tool enable/disable toggles | `Switch` widgets per tool in a detail panel |
| Tool count summary ("N Servers / M Tools") | Status bar aggregate counts |
| Tool call visualization (state + expandable I/O) | Rich tool-call log entries with collapsible detail |
| Empty states with helpful messages | Meaningful messages instead of blank widgets |
| Toast notifications | `app.notify()` calls for copy, connect, error events |

### From Studio
| Pattern | TUI Adaptation |
|---------|----------------|
| Server cards with status badges (🟢 🔴 🟡) | Color-coded status column in DataTable |
| Composable polling for status monitoring | Async polling workers with Textual timers |
| Settings tabs (General, Version, Logs) | `TabbedContent` settings screen |
| Per-server log viewer with search | `RichLog` widget per server with filter input |
| Server action dropdown (start/stop/restart) | Action bar or keybinding palette per server |
| Confirmation dialogs for destructive actions | `ModalScreen` for stop/remove operations |
| Graceful shutdown page with spinner | `LoadingIndicator` screen during teardown |
| Feature flags system | Config-based feature toggling |

---

## Existing Code Touchpoints

These files would be modified when implementing the portable features:

| File | Affected By |
|------|-------------|
| `mcp_gateway/bridge/capability_registry.py` | P0: conflict resolution, tool filtering, tool renaming |
| `mcp_gateway/constants.py` | P0: configurable timeouts |
| `mcp_gateway/config/loader.py` | P0-P2: new config schema fields |
| `mcp_gateway/bridge/forwarder.py` | P1: middleware chain, audit logging |
| `mcp_gateway/bridge/client_manager.py` | P1: health checks, P3: streamable HTTP |
| `mcp_gateway/display/logging_config.py` | P1: audit log setup |
| `mcp_gateway/tui/widgets/backend_status.py` | P1: health status display, P2: status model |
| `mcp_gateway/server/app.py` | P2: session routing, P3: incoming auth |
| `config.json` / `example_config.json` | All: new configuration fields |
| New: `mcp_gateway/bridge/middleware.py` | P1: middleware chain |
| New: `mcp_gateway/bridge/health.py` | P1: health checks |
| New: `mcp_gateway/bridge/optimizer.py` | P2: find_tool/call_tool |
| New: `mcp_gateway/bridge/audit.py` | P1: structured audit events |
