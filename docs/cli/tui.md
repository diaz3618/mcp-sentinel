# `mcp-sentinel tui`

Launch the interactive Textual-based terminal UI. The TUI connects to a running
Sentinel server via its management API and provides real-time monitoring and
control.

## Usage

```bash
mcp-sentinel tui [--server URL] [--token TOKEN] [--servers-config PATH]
```

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--server` | URL | `http://127.0.0.1:9000` | Sentinel server URL |
| `--token` | string | `None` | Bearer token for management API |
| `--servers-config` | path | `None` | Path to multi-server config (JSON) |

## Authentication

The management token can be provided via:

1. `--token` flag
2. `SENTINEL_MGMT_TOKEN` environment variable

If the server has no management token configured, no authentication is needed.

## Examples

```bash
# Connect to local server
mcp-sentinel tui

# Connect to remote server
mcp-sentinel tui --server http://192.168.1.100:9000

# With authentication
mcp-sentinel tui --server http://prod.example.com:9000 --token my-token

# Multi-server mode
mcp-sentinel tui --servers-config ~/.config/mcp-sentinel/servers.json
```

## Multi-Server Mode

Create a `servers.json` file to connect to multiple Sentinel instances:

```json
{
  "servers": {
    "local": {
      "url": "http://127.0.0.1:9000"
    },
    "staging": {
      "url": "http://staging.example.com:9000",
      "token": "staging-token"
    },
    "production": {
      "url": "http://prod.example.com:9000",
      "token": "prod-token"
    }
  }
}
```

Default location: `~/.config/mcp-sentinel/servers.json`

See the [TUI Guide](../tui/) for screen and keybinding reference.
