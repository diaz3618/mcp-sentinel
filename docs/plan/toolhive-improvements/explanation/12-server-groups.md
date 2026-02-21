# Server Groups

> **Status in analysis table:** "Explain" — Organizational feature for multi-server deployments.

---

## What It Is

Server groups let you organize backend MCP servers into **named logical collections**. Instead of a flat list of 20 servers, you group them:

- **"development"** — local dev servers, test databases, staging APIs
- **"production"** — live systems with restricted access
- **"ai-tools"** — LLM-related servers (code assistants, search, etc.)
- **"databases"** — database query and management servers

## How ToolHive Implements It

### ToolHive Core (`pkg/groups/`)
- Named groups defined in configuration
- Multiple vmcp endpoints can serve different groups
- Group-level operations: start/stop/restart all servers in a group
- Server can belong to multiple groups

### ToolHive Studio
- **Sidebar navigation** with collapsible group sections
- Groups displayed as tree nodes with server count badges
- Click a group to filter the server list
- Drag-and-drop server assignment (in some views)
- "All Servers" default view when no group is selected

### ToolHive Cloud UI
- Group-based filtering in the server catalog
- Registry entries tagged with category metadata

## How This Improves MCP Sentinel

### Without Groups
- Flat list of servers — hard to navigate with 10+ backends
- No way to batch-operate on related servers
- TUI sidebar shows every server equally — no organizational hierarchy
- Config file becomes a long undifferentiated list

### With Groups
- **TUI organization**: Sidebar shows groups as collapsible sections, each containing its member servers
- **Batch operations**: Restart all "development" servers at once
- **Selective exposure**: Only expose tools from a specific group via config profiles
- **Visual clarity**: Color-code or label groups for instant recognition
- **Config readability**: Group-based config is self-documenting

## Config Example

```json
{
  "groups": {
    "development": {
      "servers": ["local-db", "test-api", "mock-service"],
      "color": "green"
    },
    "production": {
      "servers": ["prod-db", "prod-api"],
      "color": "red"
    },
    "ai-tools": {
      "servers": ["code-assistant", "search-engine", "rag-server"],
      "color": "blue"
    }
  },
  "mcpServers": {
    "local-db": { "..." : "..." },
    "test-api": { "..." : "..." },
    "prod-db": { "..." : "..." }
  }
}
```

## TUI Integration

Groups map naturally to Textual's widget tree:

```
┌─── Server Groups ───────────┐
│ ▼ development (3 servers)   │
│   ● local-db      [healthy] │
│   ● test-api      [healthy] │
│   ● mock-service  [stopped] │
│ ▶ production (2 servers)    │
│ ▶ ai-tools (3 servers)     │
│ ─ ungrouped (1 server)     │
│   ● standalone     [healthy]│
└─────────────────────────────┘
```

Implementation would use Textual's `Tree` widget with group nodes as parents and server nodes as leaves, or a `Collapsible` container per group.

**Estimated effort:** Low — primarily a config schema addition and TUI layout change.

**Priority:** P2 — becomes essential once you have more than ~5 backends.
