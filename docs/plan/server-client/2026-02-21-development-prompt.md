# Development Prompt: Server/Client Separation for MCP Sentinel

Use this prompt to implement the server/client split in this repository.

## Prompt

You are implementing a production-safe server/client separation for MCP Sentinel.

Repository root: `/home/diaz/git/MCP-Gateway`  
Package: `mcp_sentinel`

Read these first:

- `docs/plan/server-client/2026-02-21-research.md`
- `docs/plan/server-client/2026-02-21-implementation-plan.md`

Do not assume architecture details. Verify behavior from code before changing it.

### Objectives

1. Keep MCP transport server behavior intact (`/sse`, `/messages/`).
2. Add a management control-plane API for server status and operations.
3. Convert Textual TUI to a network client for management API.
4. Ensure server can run independently of TUI lifecycle.
5. Support one TUI managing multiple server profiles.

### Hard constraints

- Keep implementation in Python.
- Do not remove existing functionality unless explicitly replaced with equivalent behavior.
- Preserve backward compatibility during migration (temporary compatibility path allowed).
- Management API must be JSON-only and versioned (`/manage/v1`).
- Management API must be secured with bearer token auth.
- Default management bind must be localhost.

### Current verified architecture (anchor points)

- `mcp_sentinel/cli.py`: current mode switching and server startup.
- `mcp_sentinel/server/lifespan.py`: startup/discovery/shutdown orchestration.
- `mcp_sentinel/tui/app.py`: embedded server startup in TUI mode.
- `mcp_sentinel/display/console.py`: callback-based status flow.
- `mcp_sentinel/bridge/*`: backend orchestration, capability registry, forwarding.

### Implement in phases

#### Phase 1: Runtime extraction

- Create a runtime service module (for example `mcp_sentinel/runtime/service.py`) to own:
  - `ClientManager`
  - `CapabilityRegistry`
  - startup/shutdown state
  - status snapshot and event history
- Refactor `server/lifespan.py` to delegate to runtime service.
- Keep current startup behavior unchanged.

#### Phase 2: Read-only management API

- Add management router (for example `mcp_sentinel/server/management/router.py`).
- Mount it in Starlette app.
- Implement endpoints:
  - `GET /manage/v1/health`
  - `GET /manage/v1/status`
  - `GET /manage/v1/backends`
  - `GET /manage/v1/capabilities`
  - `GET /manage/v1/events`
- Ensure every response is stable JSON schema (no raw MCP objects).

#### Phase 3: Security

- Add bearer-token middleware/dependency for management routes.
- Add scope model:
  - `read` for read-only endpoints
  - `admin` for mutating endpoints
- Ensure localhost bind is default for management listener.
- Add audit log entries for auth failures and admin actions.

#### Phase 4: Mutating control operations

- Implement endpoints:
  - `POST /manage/v1/reload`
  - `POST /manage/v1/backends/{name}/reconnect`
  - optional `POST /manage/v1/shutdown` (off by default)
- Add runtime lock/serialization to prevent race conditions between admin operations.

#### Phase 5: TUI remote client mode

- Stop starting Uvicorn directly from TUI client mode.
- Add management API client module for TUI (HTTP + optional SSE stream consumption).
- Replace callback plumbing with remote status/events.
- Preserve TUI UX panels with data mapped from management schemas.

#### Phase 6: Multi-server support

- Add server profile storage for TUI (named profiles with URL/token/TLS options).
- Add server selector and refresh path in TUI.
- Ensure active server context is visible in UI state.

### Suggested file additions

- `mcp_sentinel/runtime/service.py`
- `mcp_sentinel/runtime/models.py`
- `mcp_sentinel/server/management/router.py`
- `mcp_sentinel/server/management/auth.py`
- `mcp_sentinel/tui/api_client.py`
- `mcp_sentinel/tui/server_profiles.py`

### CLI updates required

Evolve CLI to explicit subcommands:

- `mcp-sentinel server ...`
- `mcp-sentinel tui ...`

Keep temporary compatibility path if needed, with deprecation warning.

### Testing requirements

Add tests for:

- runtime state transitions,
- management auth and scope checks,
- JSON schema serialization for status/backends/capabilities,
- reload/reconnect race behavior,
- TUI client mode does not control server process lifecycle.

Add at least one integration test validating:

- server process runs,
- TUI/API client fetches status,
- closing client does not stop server.

### Definition of done

- Server can run independently and continue after TUI exits.
- TUI can connect to at least one remote server using management API.
- Management API secured and localhost-by-default.
- Existing MCP data-plane endpoints still pass functional checks.
- Docs and README updated to current architecture.

### Deliverables in PR

1. Code changes for phases implemented.
2. Tests and test results.
3. Updated docs:
   - architecture overview,
   - management API contract,
   - operational/security configuration.
4. Migration notes for legacy CLI usage.

### Out of scope for this implementation PR

- Reimplementation in Rust or Go.
- Major protocol redesign beyond adding management control plane.

