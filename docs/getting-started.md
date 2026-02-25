# Getting Started

## Prerequisites

- **Python 3.10+** (3.12 or 3.13 recommended)
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip

## Installation

### With uv (recommended)

```bash
# Clone the repository
git clone https://github.com/diaz3618/mcp-sentinel.git
cd mcp-sentinel

# Install in development mode
uv pip install -e ".[yaml,dev]"
```

### With pip

```bash
pip install -e ".[yaml,dev]"
```

### Optional Extras

| Extra | Packages | Purpose |
|-------|----------|---------|
| `yaml` | `pyyaml>=6.0` | YAML config file support |
| `dev` | `black`, `mypy`, `ruff`, `textual-dev` | Development tools |

## Quick Start

### 1. Create a Config File

Sentinel looks for config files in this order:
`config.yaml` → `config.yml`

Copy and edit the example:

```bash
cp example_config.yaml config.yaml
```

A minimal config with one stdio backend:

```yaml
version: "1"

server:
  host: "127.0.0.1"
  port: 9000

backends:
  my-tool-server:
    type: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-everything"]
```

See [Configuration](configuration.md) for the full reference.

### 2. Start the Server

```bash
mcp-sentinel server
```

The server starts on `http://127.0.0.1:9000` by default. Override with flags:

```bash
mcp-sentinel server --host 0.0.0.0 --port 8080 --log-level debug
```

Or point to a specific config file:

```bash
mcp-sentinel server --config /path/to/my-config.yaml
```

### 3. Connect an MCP Client

Point any MCP-compatible client at one of the Sentinel transport endpoints:

| Transport | URL |
|-----------|-----|
| SSE | `http://127.0.0.1:9000/sse` |
| Streamable HTTP | `http://127.0.0.1:9000/mcp` |

Example — Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sentinel": {
      "url": "http://127.0.0.1:9000/sse"
    }
  }
}
```

### 4. Launch the TUI

In a separate terminal, connect the interactive TUI to the running server:

```bash
mcp-sentinel tui
```

Or connect to a remote server:

```bash
mcp-sentinel tui --server http://192.168.1.100:9000
```

### 5. Use the Management API

The management API is available at `/manage/v1/`:

```bash
# Health check (always public)
curl http://127.0.0.1:9000/manage/v1/health

# List backends
curl http://127.0.0.1:9000/manage/v1/backends

# List capabilities
curl http://127.0.0.1:9000/manage/v1/capabilities

# Hot-reload config
curl -X POST http://127.0.0.1:9000/manage/v1/reload
```

If a management token is configured, include the `Authorization` header:

```bash
curl -H "Authorization: Bearer $SENTINEL_MGMT_TOKEN" \
     http://127.0.0.1:9000/manage/v1/status
```

## Multi-Server TUI

The TUI supports connecting to multiple Sentinel instances. Create a
servers config file at `~/.config/mcp-sentinel/servers.json`:

```json
{
  "servers": [
    {
      "name": "local",
      "url": "http://127.0.0.1:9000"
    },
    {
      "name": "staging",
      "url": "http://staging.example.com:9000",
      "token": "staging-token"
    }
  ],
  "active": "local"
}
```

```bash
mcp-sentinel tui --servers-config ~/.config/mcp-sentinel/servers.json
```

## What's Next?

- [Configuration](configuration.md) — Full config reference
- [CLI Reference](cli/) — All command-line options
- [Architecture](architecture/00-overview.md) — How it works
- [Security](security/) — Authentication, RBAC, secrets
- [Management API](api/) — REST endpoint reference
