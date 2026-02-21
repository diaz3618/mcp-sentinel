# Development Roadmap — MCP Sentinel

> Phased implementation plan derived from ToolHive ecosystem analysis.  
> All features are prioritized by impact, effort, and dependency chain.

---

## Table of Contents

1. [Roadmap Overview](#roadmap-overview)
2. [Phase 0 — Foundation (Quick Wins)](#phase-0--foundation)
3. [Phase 1 — Core Infrastructure](#phase-1--core-infrastructure)
4. [Phase 2 — Advanced Features](#phase-2--advanced-features)
5. [Phase 3 — Production Readiness](#phase-3--production-readiness)
6. [Phase 4 — Ecosystem Integration](#phase-4--ecosystem-integration)
7. [Dependency Graph](#dependency-graph)
8. [Effort Estimates](#effort-estimates)

---

## Roadmap Overview

```
Phase 0 ──── Phase 1 ──── Phase 2 ──── Phase 3 ──── Phase 4
Foundation   Core Infra   Advanced     Production   Ecosystem
                                        Readiness   Integration
                                        
Config       Middleware    Optimizer    Auth (in)    AI Chat
Validation ─→ Chain ──────→ find/call   Auth (out)   Playground
                  │                     OIDC/JWT     
Conflict     Health     ──→ Session    ──→ Authorization
Resolution   Checks        Mgmt          Cedar/PDP
                  │
Tool         Audit      ──→ Backend    ──→ OpenTelemetry
Filtering    Logging       Status         Tracing
                  │        Model          Metrics
Tool         ──→ TUI                  
Renaming       Multi-Mode ─→ Registry ──→ Version
                  │          Browser      Drift
Env Var      ──→ Server                
Expansion      Groups    ──→ Client   ──→ Secrets
                             Auto-       Encrypted
Configurable               Config       Store
Timeouts                 
                          ──→ Config   ──→ Composite
Streamable                  Hot-Reload    Workflows
HTTP                        
                          ──→ Feature
                             Flags
```

---

## Phase 0 — Foundation

**Goal:** Fix immediate gaps with minimal effort. No architectural changes.  
**Estimated Total Effort:** 2-3 days

### 0.1 Config Validation (Pydantic Models)
- Add Pydantic `BaseModel` classes for config schema in `config_loader.py`
- Validate all config fields on load
- Fail fast with clear error messages on invalid config
- Auto-apply default values for optional fields
- **Effort:** 4 hours
- **Files:** `config_loader.py`

### 0.2 Conflict Resolution Strategies
- Implement `prefix`, `priority`, and `first_wins` strategies
- Configurable via `conflict_resolution.strategy` in config
- The TODO already exists in `capability_registry.py` line 42
- **Effort:** 4 hours
- **Files:** `capability_registry.py`, `config_loader.py`

### 0.3 Tool Filtering (Allow/Deny Lists)
- Per-backend `tools_filter` config with `mode: allow|deny` and `names: [...]`
- Applied in `_discover_caps_by_type()` after fetching, before aggregation
- **Effort:** 2 hours
- **Files:** `capability_registry.py`, `config_loader.py`

### 0.4 Tool Renaming / Description Override
- Per-backend `tool_overrides` config with `{original: {name, description}}`
- Reverse mapping for the forwarder
- Applied after filtering, before conflict resolution
- **Effort:** 3 hours
- **Files:** `capability_registry.py`, config files

### 0.5 Environment Variable Expansion
- Regex-based `$VAR` / `${VAR}` expansion in config string values
- Applied during config loading, before validation
- Eliminates plaintext secrets in config
- **Effort:** 1 hour
- **Files:** `config_loader.py`

### 0.6 Configurable Timeouts
- Move hardcoded constants to config with per-backend overrides
- Global defaults + per-server override pattern
- **Effort:** 2 hours
- **Files:** `config_loader.py`, all modules reading constants

### 0.7 Streamable HTTP Transport
- Add `streamablehttp_client()` support alongside `stdio_client()` and `sse_client()`
- Route to correct transport based on `transport` field in config
- **Effort:** 3 hours
- **Files:** `client_manager.py`, `config_loader.py`

---

## Phase 1 — Core Infrastructure

**Goal:** Build the architectural foundations that Phase 2+ features depend on.  
**Estimated Total Effort:** 1.5-2 weeks  
**Depends on:** Phase 0

### 1.1 Middleware Chain Architecture
- Define `MCPMiddleware` protocol and chain builder
- Refactor `forward_request()` to execute through a middleware chain
- Initial middleware: Recovery (error catch), Logging
- Config-driven middleware selection
- **Effort:** 1.5 days
- **Files:** New `middleware.py`, refactor `forwarder.py`
- **Why first:** Auth, audit, telemetry, tool filter all need this

### 1.2 Health Checks & Circuit Breaker
- Background `asyncio.Task` pinging backends every N seconds
- Health states: healthy, degraded, unhealthy, unknown
- Circuit breaker: closed → open → half-open state machine
- Optionally hide unhealthy backends from `tools/list`
- **Effort:** 2 days
- **Files:** New `health.py`, `client_manager.py`
- **Why now:** Foundation for backend status model and TUI health display

### 1.3 Audit Logging (Structured JSON)
- `structlog`-based structured JSON logging
- Audit middleware emitting events for every MCP operation
- Separate audit log file with rotation
- Fields: timestamp, event_type, backend, tool, outcome, latency_ms
- **Effort:** 1.5 days
- **Files:** New `audit.py`, middleware integration
- **Depends on:** Middleware chain (1.1)

### 1.4 TUI Multi-Mode Architecture
- Refactor `SentinelApp` to use Textual `MODES`
- Create 4 modes: Dashboard, Tools, Registry (placeholder), Settings (placeholder)
- Mode bar at top (keyboard shortcuts `1`-`4`)
- Move current dashboard content into DashboardScreen
- Add Command Palette with `SentinelCommandProvider`
- **Effort:** 2 days
- **Files:** `app.py`, new screen modules
- **Why now:** All future TUI features need multi-mode to have space

### 1.5 Server Groups
- Config schema for groups (`groups: {"dev": ["server-a", "server-b"]}`)
- Group-level operations stub
- Group display in TUI sidebar (Textual `Tree` widget)
- **Effort:** 1 day
- **Files:** `config_loader.py`, new TUI widget
- **Depends on:** TUI multi-mode (1.4)

---

## Phase 2 — Advanced Features

**Goal:** Differentiation features that go beyond basic aggregation.  
**Estimated Total Effort:** 2-3 weeks  
**Depends on:** Phase 1

### 2.1 Optimizer (find_tool / call_tool)
- In-memory tool index with text search
- `find_tool(query, limit)` meta-tool returning matching tool definitions
- `call_tool(name, args)` meta-tool routing through capability registry
- Config toggle with activation threshold (e.g., only if >30 tools)
- Token usage tracking (baseline vs. actual)
- **Effort:** 3 days
- **Files:** New `optimizer.py`, `capability_registry.py`
- **Depends on:** Tool filtering, renaming (Phase 0)

### 2.2 Backend Status Model
- `BackendPhase` enum: Pending, Initializing, Ready, Degraded, Failed, ShuttingDown
- `Condition` history per backend (timestamped messages)
- Aggregate gateway status derived from backend phases
- TUI: Color-coded phase column in BackendStatusWidget
- **Effort:** 2 days
- **Files:** New `status.py`, TUI widgets
- **Depends on:** Health checks (1.2)

### 2.3 Session Management
- `MCPSession` with routing table snapshot, TTL, affinity
- Session creation on `initialize`, cleanup on expiry
- Session ID tracking via `Mcp-Session-Id` header
- Immutable routing table per session (consistency guarantee)
- **Effort:** 3 days
- **Files:** New `session.py`, `forwarder.py`, `app.py`
- **Depends on:** Capability registry, health checks

### 2.4 Outgoing Auth (Static Headers)
- Per-backend `headers` config with env var expansion
- Headers injected during SSE/HTTP/streamable-HTTP connection
- Works alongside existing transport code
- **Effort:** 1 day
- **Files:** `client_manager.py`, `config_loader.py`
- **Depends on:** Env var expansion (0.5)

### 2.5 Registry Client
- Read-only client for MCP Registry API v0.1
- List servers, get server details, paginate results
- Multiple registry URLs in config
- **Effort:** 2 days
- **Files:** New `registry.py`, `config_loader.py`

### 2.6 TUI: Registry Browser Screen
- Registry mode with server catalog (DataTable)
- Search/filter bar
- Server detail modal (tabs: About, Tools)
- "Add to config" action
- **Effort:** 2 days
- **Files:** New TUI screen
- **Depends on:** Registry client (2.5), TUI multi-mode (1.4)

### 2.7 Client Auto-Config Export
- Templates for Claude Desktop, Cursor, VS Code, Claude Code
- Generate config snippet pointing to MCP Sentinel's endpoint
- Copy to clipboard or write to client config file
- TUI modal for template selection and preview
- **Effort:** 1 day
- **Files:** New `export.py`, TUI modal

### 2.8 Config Hot-Reload
- File watcher on config file (hash-based change detection)
- Diff old vs. new config to determine what changed
- Reconnect new/changed backends, disconnect removed ones
- No restart required for config changes
- **Effort:** 2 days
- **Files:** `config_loader.py`, `client_manager.py`

### 2.9 Feature Flags
- Config-based feature flag registry
- Check flags before enabling optional features
- TUI settings screen for toggling flags
- **Effort:** 0.5 days
- **Files:** New `features.py`, `config_loader.py`

### 2.10 YAML Config Support
- Add `pyyaml` dependency
- Auto-detect file format (`.json` vs `.yaml`/`.yml`)
- Support both formats with same Pydantic validation
- **Effort:** 0.5 days
- **Files:** `config_loader.py`

---

## Phase 3 — Production Readiness

**Goal:** Security, observability, and compliance features for shared/production deployments.  
**Estimated Total Effort:** 2-3 weeks  
**Depends on:** Phase 1 (middleware chain)

### 3.1 Incoming Authentication (JWT/OIDC)
- Starlette middleware validating Bearer tokens on SSE/HTTP connections
- OIDC discovery for public key retrieval
- Local JWT mode with shared secret
- Anonymous mode (explicit opt-in)
- User identity injected into request context
- **Effort:** 4 days
- **Files:** New `auth.py`, middleware integration, `app.py`
- **Depends on:** Middleware chain (1.1)
- **Dependencies:** `PyJWT`, `httpx` (already present)

### 3.2 Outgoing Auth (OAuth2 Client Credentials)
- Machine-to-machine token exchange for backend authentication
- Token caching with TTL-based expiry
- OAuth2 client_credentials flow
- **Effort:** 2 days
- **Files:** `client_manager.py`, new `auth_outgoing.py`
- **Depends on:** Static headers (2.4)

### 3.3 Authorization (Role-Based Policies)
- Simple role-based policies from config (admin/developer/viewer)
- Per-method, per-tool access control
- Authorization middleware in the chain
- Default deny for unmatched requests
- **Effort:** 2 days
- **Files:** New `authz.py`, middleware integration
- **Depends on:** Incoming auth (3.1)

### 3.4 OpenTelemetry Integration
- OTLP trace export with span-per-request
- Prometheus `/metrics` endpoint with counters and histograms
- Telemetry middleware in the chain
- Configurable OTLP endpoint and export interval
- **Effort:** 3 days
- **Files:** New `telemetry.py`, middleware integration
- **Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`, `prometheus-client`
- **Depends on:** Middleware chain (1.1)

### 3.5 Encrypted Secret Store
- AES-256-GCM encrypted secrets file
- `${secret:name}` reference syntax in config
- CLI/TUI interface for managing secrets
- Key derivation from master password
- **Effort:** 2 days
- **Files:** New `secrets.py`, `config_loader.py`
- **Dependencies:** `cryptography`

---

## Phase 4 — Ecosystem Integration

**Goal:** Advanced features that complete the ToolHive feature parity and add unique MCP Sentinel capabilities.  
**Estimated Total Effort:** 3-4 weeks  
**Depends on:** Phase 2-3 as noted

### 4.1 Composite Tool Workflows
- YAML workflow definitions with DAG-based execution
- topological sort via `graphlib.TopologicalSorter`
- Parallel step execution with `asyncio.gather()`
- Template expansion (Jinja2) for step argument injection
- Failure modes: abort, continue, retry
- Virtual tools registered in capability registry
- **Effort:** 1 week
- **Files:** New `composer.py`, `workflow_parser.py`
- **Depends on:** Middleware chain, session management

### 4.2 Elicitation Protocol
- Handle MCP elicitation messages during workflow steps
- TUI modal for user input during workflow execution
- Pass user responses back to the workflow engine
- **Effort:** 3 days
- **Depends on:** Composite workflows (4.1), TUI multi-mode (1.4)

### 4.3 AI Chat Playground
- Built-in LLM chat interface in TUI
- Model selector (configurable API endpoints)
- MCP server/tool picker for the conversation
- Streaming markdown rendering in `RichLog`
- Tool call visualization with expandable I/O
- **Effort:** 1 week
- **Files:** New TUI mode + LLM client
- **Depends on:** TUI multi-mode (1.4), capability registry

### 4.4 Version Drift Detection
- Compare local server versions against registry
- TUI notification for available updates
- One-action update (for stdio servers via pip/npm)
- **Effort:** 2 days
- **Depends on:** Registry client (2.5)

### 4.5 Tool Customization TUI
- Dedicated tool editor screen
- Per-tool enable/disable with visual toggles
- Inline description editing
- Diff view (original vs. customized)
- Save to config
- **Effort:** 3 days
- **Depends on:** Tool renaming (0.4), tool filtering (0.3), TUI multi-mode (1.4)

---

## Dependency Graph

```
Phase 0 (no dependencies):
  0.1 Config Validation
  0.2 Conflict Resolution
  0.3 Tool Filtering
  0.4 Tool Renaming
  0.5 Env Var Expansion
  0.6 Configurable Timeouts
  0.7 Streamable HTTP

Phase 1 (depends on Phase 0):
  1.1 Middleware Chain
  1.2 Health Checks
  1.3 Audit Logging ← 1.1
  1.4 TUI Multi-Mode
  1.5 Server Groups ← 1.4

Phase 2 (depends on Phase 0-1):
  2.1 Optimizer ← 0.3, 0.4
  2.2 Backend Status ← 1.2
  2.3 Session Mgmt ← 1.2
  2.4 Outgoing Auth (static) ← 0.5
  2.5 Registry Client
  2.6 Registry TUI ← 2.5, 1.4
  2.7 Client Auto-Config
  2.8 Config Hot-Reload
  2.9 Feature Flags
  2.10 YAML Config

Phase 3 (depends on Phase 1):
  3.1 Incoming Auth ← 1.1
  3.2 Outgoing Auth (OAuth2) ← 2.4
  3.3 Authorization ← 3.1
  3.4 OpenTelemetry ← 1.1
  3.5 Encrypted Secrets

Phase 4 (depends on Phase 2-3):
  4.1 Composite Workflows ← 1.1, 2.3
  4.2 Elicitation ← 4.1, 1.4
  4.3 AI Chat Playground ← 1.4
  4.4 Version Drift ← 2.5
  4.5 Tool Customization TUI ← 0.3, 0.4, 1.4
```

---

## Effort Estimates

| Phase | Items | Estimated Duration | Dependencies |
|-------|-------|--------------------|--------------|
| **Phase 0** | 7 items | 2-3 days | None |
| **Phase 1** | 5 items | 1.5-2 weeks | Phase 0 |
| **Phase 2** | 10 items | 2-3 weeks | Phase 1 |
| **Phase 3** | 5 items | 2-3 weeks | Phase 1 |
| **Phase 4** | 5 items | 3-4 weeks | Phase 2-3 |
| **Total** | **32 items** | **~10-14 weeks** | Sequential |

Phases 2 and 3 can run in parallel since they share only Phase 1 as a dependency. This brings the realistic timeline to **~8-10 weeks** with parallel execution.

### Priority Order Within Phases

If time is limited, prioritize within each phase:

**Phase 0 must-haves:** 0.2 (conflict resolution), 0.3 (filtering), 0.5 (env vars)  
**Phase 1 must-haves:** 1.1 (middleware), 1.2 (health), 1.4 (TUI modes)  
**Phase 2 must-haves:** 2.1 (optimizer), 2.5 (registry), 2.7 (client config)  
**Phase 3 must-haves:** 3.1 (JWT auth), 3.4 (OpenTelemetry)  
**Phase 4 must-haves:** 4.3 (AI chat) — unique differentiator
