# Streamable HTTP Transport

> **Status in analysis table:** "Yes" — This is a gap MCP Sentinel needs to fill.

---

## What It Is

Streamable HTTP is the **new standard MCP transport** that replaces SSE (Server-Sent Events). The MCP specification is deprecating SSE in favor of streamable HTTP because it:

- Works over standard HTTP POST/GET (no special SSE connection management)
- Supports bidirectional streaming within a single HTTP request
- Is more compatible with load balancers, CDNs, and proxies
- Doesn't require a persistent connection for the full session

## How ToolHive Implements It

ToolHive's `pkg/transport/` package supports all three transports through a factory pattern:

```
TransportFactory.Create(type) → Transport
  ├── "stdio"            → StdioBridge
  ├── "sse"              → SSE proxy
  └── "streamable-http"  → StreamableHTTP client
```

The streamable HTTP transport in ToolHive:
- Lives in `pkg/transport/streamable/`
- Uses the standard `net/http` client (no special libraries)
- Sends MCP JSON-RPC messages as HTTP POST bodies
- Receives streaming responses via chunked transfer encoding
- Supports session headers (`Mcp-Session-Id`) for stateful conversations

## How This Improves MCP Sentinel

Currently, MCP Sentinel supports two backend transports:
- **stdio** — subprocess-based, via `mcp` SDK's `stdio_client()`
- **SSE** — via `mcp` SDK's `sse_client()`

Adding streamable HTTP means MCP Sentinel can connect to **any MCP server**, including:
- Cloud-hosted MCP servers that only support streamable HTTP
- Servers behind corporate proxies that block SSE connections
- The growing number of servers migrating away from SSE as the spec evolves

## Implementation Path for MCP Sentinel

The Python `mcp` SDK already supports streamable HTTP via `streamablehttp_client()`. The implementation would:

1. Add `"streamable-http"` as a recognized transport type in `config.json`
2. In `client_manager.py`, add a `_init_streamablehttp_backend()` method alongside the existing `_init_sse_backend()` and `_init_stdio_backend()`
3. Use `from mcp.client.streamable_http import streamablehttp_client`
4. Route to the correct init method based on transport type in config

**Estimated effort:** Low — the SDK does the heavy lifting.

## Config Example

```json
{
  "mcpServers": {
    "cloud-server": {
      "transport": "streamable-http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer $API_TOKEN"
      }
    }
  }
}
```
