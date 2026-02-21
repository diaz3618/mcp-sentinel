# Client Auto-Configuration

> **Status in analysis table:** "Explain" — Quality-of-life feature for connecting AI clients.

---

## What It Is

Client auto-config generates **ready-to-use configuration snippets** for popular AI clients (Claude Desktop, Cursor, VS Code, Claude Code) that point to MCP Sentinel's endpoint. Instead of manually editing each client's config file, MCP Sentinel generates the snippet and optionally writes it directly.

## How ToolHive Implements It

### ToolHive Studio
Studio has a dedicated "Client Management" section that:
1. **Detects installed AI clients** on the system
2. **Generates configuration** for each detected client
3. **Writes the configuration** directly to the client's config file
4. **Validates** the written config matches the expected format

Supported clients in Studio:
- **GitHub Copilot** (VS Code) — writes to VS Code's `settings.json` under `mcp.servers`
- **Cursor** — writes to `~/.cursor/mcp.json`
- **Claude Code** — writes to `~/.claude/claude_desktop_config.json`

### ToolHive Cloud UI
Cloud UI generates **deeplinks** instead of writing files directly (since it's a web app):
- Click "Add to Cursor" → opens `cursor://settings/mcp?config=...`
- Click "Add to VS Code" → opens `vscode://settings/...`
- Click "Copy config" → copies JSON snippet to clipboard

The generated config points to the MCP server's SSE/HTTP endpoint with any required headers.

## How This Improves MCP Sentinel

### Without Auto-Config
Users must manually:
1. Find the correct config file location for each AI client
2. Know the exact JSON structure each client expects
3. Copy the MCP Sentinel endpoint URL
4. Add any required headers
5. Restart the client to apply changes

This is error-prone and different for every client. A single misplaced comma in JSON breaks the config.

### With Auto-Config
- **One-click setup**: Select a client, MCP Sentinel generates the config
- **Correct by construction**: Config format matches what each client expects
- **TUI command**: `sentinel config export --client cursor` from the command palette
- **Copy to clipboard**: For clients MCP Sentinel can't write to directly
- **Endpoint awareness**: Config automatically uses the correct URL/port from MCP Sentinel's running config

## Implementation Path for MCP Sentinel

### Config Templates per Client

```python
CLIENT_TEMPLATES = {
    "claude_desktop": {
        "path": "~/.claude/claude_desktop_config.json",
        "template": {
            "mcpServers": {
                "{name}": {
                    "command": "...",  # or URL for SSE
                    "args": [],
                }
            }
        }
    },
    "cursor": {
        "path": "~/.cursor/mcp.json",
        "template": {
            "mcpServers": {
                "{name}": {
                    "url": "{endpoint}",
                    "transport": "sse"
                }
            }
        }
    },
    "vscode": {
        "path": "~/.vscode/settings.json",
        "key": "mcp.servers",
        "template": {
            "{name}": {
                "type": "sse",
                "url": "{endpoint}"
            }
        }
    }
}
```

### TUI Integration

Add a "Export Config" action to the toolbar or command palette:

```
┌─── Export Client Config ────────────────┐
│                                         │
│  Select target client:                  │
│  ○ Claude Desktop                       │
│  ● Cursor                               │
│  ○ VS Code (GitHub Copilot)             │
│  ○ Claude Code (CLI)                    │
│  ○ Copy JSON to clipboard               │
│                                         │
│  Generated config:                      │
│  ┌─────────────────────────────────┐    │
│  │ {                               │    │
│  │   "mcpServers": {              │    │
│  │     "mcp-sentinel": {          │    │
│  │       "url": "http://localhost: │    │
│  │         8080/sse",             │    │
│  │       "transport": "sse"       │    │
│  │     }                          │    │
│  │   }                            │    │
│  │ }                              │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [Copy]  [Write to File]  [Cancel]      │
└─────────────────────────────────────────┘
```

### CLI Integration

```bash
# Print config snippet
mcp-sentinel export --client cursor

# Write directly to client config
mcp-sentinel export --client cursor --write

# All clients
mcp-sentinel export --all
```

**Estimated effort:** Low — template-based string formatting with known config file paths.

**Priority:** P2 — significant quality-of-life improvement. Every user needs to configure at least one AI client.
