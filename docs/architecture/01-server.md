# Server & Transport Layer

The server layer accepts incoming MCP client connections and exposes the
management REST API. It is built on Starlette (ASGI) and served by Uvicorn.

## ASGI Application

`mcp_sentinel/server/app.py` constructs the Starlette application with these
routes:

| Route | Method | Purpose |
|-------|--------|---------|
| `/sse` | GET | SSE transport — MCP client connections |
| `/messages/` | POST | SSE transport — client message submission |
| `/mcp` | GET, POST, DELETE | Streamable HTTP transport |
| `/manage/v1/*` | various | Management REST API (mounted sub-app) |

Both transports are always available regardless of the `server.transport` config
setting.

## Transport Details

### SSE (Server-Sent Events)

The SSE transport uses `mcp.server.sse.SseServerTransport`:

1. Client sends `GET /sse` — receives an SSE stream
2. Server sends a `endpoint` event with the POST URL for messages
3. Client sends MCP protocol messages via `POST /messages/`
4. Responses stream back over the SSE connection

### Streamable HTTP

The Streamable HTTP transport uses `mcp.server.streamable_http.StreamableHTTPServerTransport`:

1. Client sends requests to `POST /mcp`
2. Each request gets its own transport instance
3. Sessions are tracked via `Mcp-Session-Id` header
4. Supports `GET /mcp` for SSE streaming and `DELETE /mcp` for session cleanup

## Lifecycle

`mcp_sentinel/server/lifespan.py` manages startup and shutdown via Starlette's
async context manager pattern:

### Startup Sequence

1. Determine config path (CLI flag → env var → auto-detect)
2. Create `SentinelService`
3. Call `service.start(config_path)` — connects all backends
4. Attach bridge components to MCP server:
   - `manager` (ClientManager)
   - `registry` (CapabilityRegistry)
   - `AuditLogger`
   - Middleware chain
   - `ToolIndex` (if optimizer enabled)
   - `SessionManager`
   - `FeatureFlags`
5. Propagate service to management sub-app state

### Shutdown Sequence

1. Stop `SessionManager`
2. Call `service.stop()` — disconnects all backends
3. Console status update

## MCP Protocol Handlers

`mcp_sentinel/server/handlers.py` registers handlers on the MCP server instance:

| Handler | MCP Method | Behavior |
|---------|-----------|----------|
| `list_tools` | `tools/list` | Returns aggregated tools (or meta-tools if optimizer active) |
| `list_resources` | `resources/list` | Returns aggregated resources |
| `list_prompts` | `prompts/list` | Returns aggregated prompts |
| `call_tool` | `tools/call` | Routes through middleware chain to correct backend |
| `read_resource` | `resources/read` | Routes through middleware chain |
| `get_prompt` | `prompts/get` | Routes through middleware chain |

### Optimizer Meta-Tools

When the tool optimizer is enabled, `list_tools` returns meta-tools instead of
the full catalog:

- **`find_tool`** — Search the tool index by query string
- **`call_tool`** — Invoke a tool by name with arguments

Plus any tools listed in `optimizer.keep_tools`.

The `call_tool` handler detects these meta-tool names and delegates to the
`ToolIndex` before reaching the middleware chain.

## Session Management

`mcp_sentinel/server/session/` tracks active client connections:

- **`SessionManager`** — Creates, tracks, and expires sessions
- **`SessionInfo`** — Per-session state: transport type, tool usage, capability
  snapshots, TTL, idle detection
- Sessions are cleaned up on disconnect or TTL expiry
- Session data is available via `GET /manage/v1/sessions`
