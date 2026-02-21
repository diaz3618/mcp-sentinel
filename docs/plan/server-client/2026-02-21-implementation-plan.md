# MCP Sentinel Server/Client Separation Implementation Plan

Date: 2026-02-21  
Depends on: `docs/plan/server-client/2026-02-21-research.md`

## 1) Goal

Split MCP Sentinel into:

- a standalone server process (MCP data plane + management control plane), and
- a separate Textual TUI client that connects over the management API.

Primary outcomes:

- server uptime independent from TUI lifetime,
- secure management interface,
- one TUI managing multiple servers.

## 2) Non-Goals (for this migration)

- Rewriting MCP forwarding logic in another language.
- Replacing Starlette/Uvicorn stack.
- Breaking existing `--no-tui` behavior during initial phases.

## 3) Current-State Constraints (Verified)

- TUI mode embeds Uvicorn in-process (`mcp_sentinel/tui/app.py`).
- Startup/discovery/shutdown logic is concentrated in `server/lifespan.py`.
- TUI status is in-process callback-driven (`display/console.py`), not network-driven.
- There is no management API surface today.

## 4) Target Architecture

## 4.1 Planes

- Data plane (existing): MCP transport (`/sse`, `/messages/`).
- Control plane (new): management API for status, inventory, lifecycle operations, events.

## 4.2 Runtime core

Introduce a runtime service abstraction (single source of truth for server state):

- owns `ClientManager`, `CapabilityRegistry`, startup state, health flags,
- exposes `start()`, `stop()`, `snapshot()`, `reload_config()`, `reconnect_backend(name)`.

`server/lifespan.py` should delegate to this runtime service instead of containing full orchestration logic directly.

## 4.3 UI model

- TUI stops launching Uvicorn directly.
- TUI connects to management API and renders remote state/events.
- TUI stores multiple server profiles and switches active target.

## 5) Management API Contract (v1 draft)

Prefix: `/manage/v1`

Read-only endpoints:

- `GET /health`
- `GET /status`
- `GET /backends`
- `GET /capabilities`
- `GET /events` (paged/event-log view)
- `GET /events/stream` (SSE control-plane events)

Mutating endpoints (admin scope):

- `POST /reload` (reload config + reconnect/discovery)
- `POST /backends/{name}/reconnect`
- `POST /shutdown` (optional, off by default)

Response shape requirements:

- JSON serializable only (no raw MCP Python objects).
- Include monotonic revision/cursor for event/state updates.
- Include explicit `startup_state` enum (`starting`, `ready`, `degraded`, `failed`, `stopping`, `stopped`).

## 6) Security Plan

Defaults:

- Bind management API to `127.0.0.1`.
- Require bearer token for management API.

Optional hardening:

- TLS termination on management listener.
- mTLS mode for server-to-admin-client deployments.
- Auth scopes (`read`, `admin`) for endpoint authorization.
- Audit log entries for mutating operations.

Implementation notes:

- Add Starlette auth middleware/dependency for management routes.
- Keep data-plane MCP transport auth separate from management auth.

## 7) CLI Evolution

Phase-in command model:

- `mcp-sentinel server ...` -> server only (no TUI)
- `mcp-sentinel tui ...` -> TUI client only
- legacy mode retained temporarily for compatibility and deprecation warning

Suggested new options:

- `--management-host`
- `--management-port`
- `--management-token-env`
- `--management-tls-cert`, `--management-tls-key`
- `--management-mtls-ca`

## 8) Phased Delivery Plan

## Phase 0: Prep and safety rails

- Add architecture decision record in docs.
- Add JSON-serializable runtime status models.
- Add minimal test scaffold for runtime and API handlers.

Exit criteria:

- Can construct status snapshot without TUI callback path.

## Phase 1: Extract runtime service

- Move startup/discovery/shutdown orchestration from `server/lifespan.py` into a runtime service module.
- Keep behavior identical for existing startup path.

Exit criteria:

- Existing `--no-tui` behavior unchanged.
- Existing MCP endpoints still functional.

## Phase 2: Add read-only management API

- Add management router and mount in Starlette app.
- Implement `health`, `status`, `backends`, `capabilities`, `events` endpoints.
- Convert status payloads to stable JSON schemas.

Exit criteria:

- A separate client can read live server state with no in-process callback.

## Phase 3: Secure management API

- Implement bearer token auth + scope checks.
- Add localhost default bind and explicit remote enable flag.
- Add audit log events for auth failures and admin calls.

Exit criteria:

- Unauthenticated management calls are rejected.

## Phase 4: Add mutating operations

- Implement `reload`, per-backend reconnect, optional shutdown endpoint.
- Add runtime locks to prevent concurrent destructive actions.

Exit criteria:

- Reload/reconnect are idempotent and race-safe.

## Phase 5: Convert TUI to remote client mode

- Remove embedded Uvicorn startup from `tui/app.py` for client mode.
- Replace callback plumbing with management API client + event stream consumer.
- Keep temporary embedded compatibility mode behind explicit flag if needed.

Exit criteria:

- Closing TUI does not stop server.

## Phase 6: Multi-server management UX

- Add server profile storage and selector in TUI.
- Support switching target server and refreshing panels per target.

Exit criteria:

- One TUI can manage multiple independent servers.

## Phase 7: Cleanup and deprecation

- Deprecate/remove legacy in-process mode when safe.
- Update README and operational docs to current architecture.

Exit criteria:

- Docs match actual module/CLI behavior.

## 9) Testing Strategy

- Unit tests:
  - runtime state transitions,
  - auth middleware/scope checks,
  - serialization of capability/status payloads.
- Integration tests:
  - start server-only mode,
  - TUI-client/API-client fetches status and events,
  - reload/reconnect operations.
- Failure tests:
  - backend unavailable,
  - partial backend failure,
  - invalid token,
  - concurrent admin operations.

## 10) Risks and Mitigations

Risk: Runtime mutation races (reload vs reconnect vs shutdown).  
Mitigation: single runtime coordinator with `asyncio.Lock` and explicit operation queue.

Risk: TUI regression when moving from callbacks to network transport.  
Mitigation: phase with dual-path compatibility until parity is validated.

Risk: Schema drift between server and TUI.  
Mitigation: versioned management API and typed response models.

Risk: Management port exposure.  
Mitigation: localhost-by-default + token auth + optional TLS/mTLS.

## 11) Rust/Go Parallel Implementation Gate

Do not start Rust/Go implementation until after Phase 3 or Phase 4, when management/data-plane contracts are stable.

Gate criteria:

- management API schema is versioned and tested,
- server runtime semantics are documented,
- baseline Python performance and reliability metrics are captured.

Then evaluate Rust/Go prototypes against measured requirements rather than assumptions.

## 12) Immediate Next Development Slice

If only one slice is funded first, implement Phases 1-3:

- runtime extraction,
- read-only management API,
- token-secured management access.

That delivers independent operations and enables remote client development with minimal architectural risk.
