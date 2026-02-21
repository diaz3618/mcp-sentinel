# MCP Server Registry

> **Status in analysis table:** "Explain" — Discovery and catalog feature.

---

## What It Is

A registry is a **curated catalog of MCP servers** — their names, descriptions, transport endpoints, tool lists, and versions. Instead of manually configuring every server by URL, users browse a catalog, pick servers, and add them with one click.

Think of it like a package registry (npm, PyPI) but for MCP servers.

## How ToolHive Implements It

### ToolHive Registry Server (`toolhive-registry-server/`)

A standalone Go service with PostgreSQL backing:

#### MCP Registry API v0.1
Standards-compliant API (following the emerging MCP Registry specification):

| Endpoint | Purpose |
|----------|---------|
| `GET /v0/servers` | List registered servers (paginated) |
| `GET /v0/servers/{name}` | Get server details |
| `GET /v0/servers/{name}/versions` | List versions of a server |
| `POST /v0/servers` | Publish a new server entry |
| `DELETE /v0/servers/{name}` | Remove a server entry |

#### Data Model
```
registry
  └── registry_entry
        └── mcp_server
              ├── mcp_server_package (container image, versioned)
              └── mcp_server_remote (SSE/HTTP endpoint)
```

Each server entry includes:
- Name, description, icon URL
- Transport type (stdio, SSE, streamable-http)
- Connection details (image/URL)
- Tool definitions (what the server exposes)
- Version history
- Categories/tags for browsing

#### 5 Data Source Types
The registry can ingest servers from:
1. **Git** — YAML/JSON files in Git repositories
2. **API** — Pull from another registry's API
3. **File** — Local filesystem directory
4. **Managed** — Directly published via API
5. **Kubernetes** — Discover from K8s CRDs

#### Background Sync
A coordinator runs every 2 minutes:
- Polls configured data sources for changes
- Uses hash-based change detection (only re-processes if content hash differs)
- Adds random jitter to prevent thundering herd

#### Skills System
An extension beyond basic server registry:
- Skills represent higher-level capabilities (not raw tools)
- Linked to OCI containers or Git repositories
- Tagged and searchable

### ToolHive Cloud UI — Registry Browser
- **Grid/list toggle** for browsing servers
- **Search bar** with real-time filtering by name/description
- **Category filters** for narrowing results
- **Server detail page** with tabs: About (description, transport, connection details) and Tools (full tool list with schemas)
- **"Add to client" button** generating deeplinks for Cursor, VS Code, Claude Desktop

### ToolHive Studio — Registry Integration
- **Registry tab** in navigation for browsing
- **Version drift detection** — compares local server version against registry, shows badge if update available
- **One-click install** from registry to local setup

## How This Improves MCP Sentinel

### Without a Registry
- Users must manually find MCP server URLs/configs from documentation
- No discovery mechanism — you need to already know what exists
- No version tracking — no way to know if a newer version is available
- Adding a new server requires editing config.json by hand

### With Registry Support
- **Browse and discover** MCP servers from the TUI
- **One-command add**: Select a server from the registry and it's automatically added to config
- **Version awareness**: Know when backends have updates available
- **Community sharing**: Connect to public registries to find community servers
- **Self-hosted catalog**: Organizations can run their own registry for internal servers

## Implementation Path for MCP Sentinel

### Phase 1: Registry Client (Read-Only)

```python
class RegistryClient:
    """Read-only client for MCP Registry API v0.1"""
    
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url)
    
    async def list_servers(self, cursor: str | None = None, limit: int = 20) -> ServerPage:
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        resp = await self._client.get("/v0/servers", params=params)
        return ServerPage.from_response(resp.json())
    
    async def get_server(self, name: str) -> ServerEntry:
        resp = await self._client.get(f"/v0/servers/{name}")
        return ServerEntry.from_response(resp.json())
```

### Phase 2: TUI Registry Browser

A new TUI screen (via Textual `Mode`) for browsing:
```
┌─── Registry ─────────────────────────────────────┐
│ Search: [_________________]  Registry: [default ▼]│
│                                                   │
│ Name              Transport   Tools  Version      │
│ ─────────────────────────────────────────────     │
│ github-mcp        SSE         12     v2.1.0       │
│ postgres-mcp      stdio       8      v1.3.0       │
│ slack-mcp         HTTP        15     v3.0.0       │
│ filesystem-mcp    stdio       6      v1.0.0       │
│                                                   │
│ [Enter] View Details  [A] Add to Config  [/] Search│
└───────────────────────────────────────────────────┘
```

### Phase 3: Auto-Config Generation
When a user selects a server to add, generate the config entry:
```json
{
  "slack-mcp": {
    "transport": "sse",
    "url": "https://mcp.slack.com/sse",
    "headers": {},
    "from_registry": "https://registry.toolhive.dev",
    "registry_version": "v3.0.0"
  }
}
```

### Config Example

```json
{
  "registries": [
    {
      "name": "toolhive-official",
      "url": "https://registry.toolhive.dev",
      "auth": {
        "type": "bearer",
        "token": "$REGISTRY_TOKEN"
      }
    },
    {
      "name": "internal",
      "url": "https://registry.internal.corp/v0"
    }
  ]
}
```

**Estimated effort:** Medium for read-only client, Medium-High for TUI browser.

**Priority:** P2 — becomes valuable as the MCP ecosystem grows and more public registries appear.
