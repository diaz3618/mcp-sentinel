# TUI Guide

MCP Sentinel includes an interactive terminal UI built with
[Textual](https://textual.textualize.io/). The TUI connects to a running
Sentinel server via the management API and provides real-time monitoring,
capability browsing, and server control.

## Launching

```bash
# Connect to local server (default: http://127.0.0.1:9000)
mcp-sentinel tui

# Connect to remote server
mcp-sentinel tui --server http://192.168.1.100:9000

# With authentication
mcp-sentinel tui --token my-management-token

# Multi-server mode
mcp-sentinel tui --servers-config ~/.config/mcp-sentinel/servers.json
```

See [`mcp-sentinel tui`](../cli/tui.md) for all CLI options.

## Screens

The TUI has four main screens, accessible via keybindings or the command palette.

### Dashboard (key: `1` or `d`)

The default screen showing an overview of the Sentinel instance:

- **Server Info** — Name, version, uptime, transport URLs
- **Backend Status** — Connection state and health for each backend, color-coded
  by lifecycle phase (Ready=green, Degraded=yellow, Failed=red)
- **Event Log** — Real-time event stream with severity indicators
- **Capability Summary** — Quick counts of tools, resources, and prompts

### Tools (key: `2`)

Full-screen capability explorer:

- Browse all aggregated tools, resources, and prompts
- Filter by capability type (key: `t` tools, `r` resources, `p` prompts)
- Search by name
- View detailed capability information including schemas

### Registry (key: `3`)

Server browser and discovery:

- Browse available MCP servers from the registry
- View server details and metadata
- Install panel for adding new backends

### Settings (key: `4` or `s`)

Configuration and preferences:

- View current config (read from server)
- Theme selection
- TUI preferences

## Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `1` or `d` | Switch to Dashboard |
| `2` | Switch to Tools |
| `3` | Switch to Registry |
| `4` or `s` | Switch to Settings |
| `t` | Show Tools tab |
| `r` | Show Resources tab |
| `p` | Show Prompts tab |
| `n` | Cycle theme |
| `T` (Shift) | Open theme picker |
| `Ctrl+P` | Command palette |

## Command Palette

Press `Ctrl+P` to open the command palette with quick access to:

- Dashboard Mode
- Tools Mode
- Registry Mode
- Settings Mode
- Show Server Details
- Show Connection Info
- Show Tools/Resources/Prompts Tab
- Open Theme Picker
- Cycle Theme

## Polling

The TUI polls the management API every 2 seconds to refresh:

- Health status
- Backend states
- Capabilities
- Events

### Connection Handling

- **Connection lost**: TUI shows a connection-lost indicator and continues
  polling. It will reconnect automatically when the server becomes available.
- **Connection restored**: TUI resumes normal operation and refreshes all data.

## Multi-Server Mode

With a `servers.json` config, the TUI shows a server selector widget allowing
you to switch between multiple Sentinel instances:

```json
{
  "servers": {
    "local": { "url": "http://127.0.0.1:9000" },
    "staging": { "url": "http://staging:9000", "token": "tok" }
  }
}
```

The server selector appears at the top of the dashboard. Selecting a different
server reconnects the TUI to that instance.

## Theming

The TUI supports Textual's built-in themes. Cycle through themes with `n` or
open the theme picker with `T` (Shift+T) for a visual preview.

## Additional Screens

| Screen | Purpose |
|--------|---------|
| Tool Editor | Edit tool parameters and test invocation |
| Skills | Browse and manage installed skill packs |
| Elicitation | Handle elicitation requests from backends |
| Theme Picker | Visual theme selection with previews |

See [Screens Reference](screens.md) for detailed screen documentation.
