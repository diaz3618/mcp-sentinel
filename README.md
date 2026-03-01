# MCP Sentinel

[![Docker Hub Pulls](https://img.shields.io/docker/pulls/diaz3618/mcp-sentinel?logo=docker&label=Docker%20Hub%20pulls)](https://hub.docker.com/r/diaz3618/mcp-sentinel)
[![GHCR Pulls](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fdiaz3618%2Fmcp-sentinel&query=%24.downloadCount&label=GHCR%20pulls&logo=github)](https://ghcr.io/diaz3618/mcp-sentinel)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for more details.

## Project Overview

MCP Sentinel is a **central gateway and management platform** for MCP (Model Context Protocol) servers. It connects to and aggregates capabilities from multiple backend MCP servers (stdio, SSE, or streamable-HTTP) and exposes them to upstream MCP clients through **SSE** (`/sse`) and **Streamable HTTP** (`/mcp`) transports.

The project has a **server/client architecture**:

- **`mcp-sentinel server`** — Headless server that runs the MCP bridge, management API, and transports.
- **`mcp-sentinel tui`** — Textual-based terminal UI that connects to a running server over HTTP.
- **`mcp-sentinel secret`** — Manage encrypted secrets (set, get, list, delete).

**Core Advantages:**

1. **Simplified Client Configuration:** MCP clients connect to one MCP Sentinel address to access all backend services.
2. **Capability Aggregation:** Aggregates MCP tools, resources, and prompts from multiple sources into a single endpoint.
3. **Management API:** RESTful API at `/manage/v1/` for runtime inspection and control of backend services.
4. **Multi-Server TUI:** Connect the TUI to multiple Sentinel servers simultaneously and switch between them.
5. **Security:** JWT/OIDC authentication, RBAC authorization, encrypted secret storage, and log redaction.

## Installation and Setup

Requires Python 3.10+. Using `uv` for environment management is recommended.

Alternatively, run with **Docker** — see the [Docker usage guide](docs/docker.md).

1. **Clone Repository**

    ```bash
    git clone https://github.com/diaz3618/mcp-sentinel.git
    cd mcp-sentinel
    ```

2. **Create and Activate Virtual Environment**

    ```bash
    uv venv
    source .venv/bin/activate   # Linux/macOS
    # .venv\Scripts\activate    # Windows
    ```

3. **Install Dependencies**

    ```bash
    uv sync
    ```

## Quick Start

### View Help

```bash
mcp-sentinel --help
```

```text
usage: mcp-sentinel [-h] {server,tui,secret} ...

MCP Sentinel v0.5.0

positional arguments:
  {server,tui,secret}
    server       Run the headless Sentinel server (Uvicorn + MCP bridge)
    tui          Launch the Textual TUI connected to a running Sentinel server
    secret       Manage encrypted secrets (set, get, list, delete)

options:
  -h, --help     show this help message and exit
```

### Start the Server

```bash
# Default: listen on 127.0.0.1:9000, auto-detect config file
mcp-sentinel server

# Custom host, port, and log level
mcp-sentinel server --host 0.0.0.0 --port 8080 --log-level debug

# Explicit config file
mcp-sentinel server --config /path/to/config.yaml
```

Config file resolution order: `--config` flag → `SENTINEL_CONFIG` env var → auto-detect (`config.yaml` → `config.yml`).

The server exposes:

- **SSE endpoint** at `http://<host>:<port>/sse` — for MCP clients using the SSE transport.
- **Streamable HTTP endpoint** at `http://<host>:<port>/mcp` — for MCP clients using the newer Streamable HTTP transport.
- **Management API** at `http://<host>:<port>/manage/v1/` — for the TUI and automation.

Set the `SENTINEL_MGMT_TOKEN` environment variable to enable bearer token authentication on the management API.

### Launch the TUI

```bash
# Connect to a local server
mcp-sentinel tui --server http://127.0.0.1:9000

# With authentication
mcp-sentinel tui --server http://127.0.0.1:9000 --token YOUR_TOKEN

# Multi-server mode (uses ~/.config/mcp-sentinel/servers.json)
mcp-sentinel tui --servers-config /path/to/servers.json
```

### Multi-Server Configuration

Create a `servers.json` file to manage multiple Sentinel servers:

```json
{
  "servers": [
    {
      "name": "local",
      "url": "http://127.0.0.1:9000"
    },
    {
      "name": "production",
      "url": "https://sentinel.example.com:9000",
      "token": "your-production-token"
    }
  ],
  "active": "local"
}
```

Default location: `~/.config/mcp-sentinel/servers.json`

### MCP Client Connection

After starting the server, connect any MCP-compatible client to one of the transport endpoints:

| Transport | URL |
|-----------|-----|
| SSE | `http://<host>:<port>/sse` |
| Streamable HTTP | `http://<host>:<port>/mcp` |

Supported clients include Claude Desktop, Cursor, Cline, and any other MCP-compatible application.

### Logs

Runtime logs are saved in the `logs/` directory with timestamped filenames.

## Configuration

The configuration file defines both server settings and backend MCP server connections.

### Config Format (YAML)

The config uses a versioned YAML format with server settings and backend definitions:

```yaml
version: "1"

server:
  host: "0.0.0.0"
  port: 9000
  transport: sse                # "sse" or "streamable-http"
  management:
    enabled: true
    token: "${SENTINEL_MGMT_TOKEN}"

backends:
  my_stdio_server:
    type: stdio
    command: python
    args: ["path/to/server.py"]
    env:
      API_KEY: "${MY_API_KEY}"

  remote_sse:
    type: sse
    url: "https://mcp.example.com/sse"

  remote_streamable:
    type: streamable-http
    url: "https://mcp.example.com/mcp"
```

### Backend Types

**stdio** — Local MCP server processes managed by Sentinel.

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"stdio"` |
| `command` | Yes | Executable to run |
| `args` | No | Command arguments (default: `[]`) |
| `env` | No | Environment variables |

**sse** — Connect to MCP servers over SSE; optionally start a local process.

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"sse"` |
| `url` | Yes | SSE endpoint URL |
| `command` | No | Optional local process to start |
| `args` | No | Command arguments |
| `headers` | No | Extra HTTP headers |
| `auth` | No | Outgoing auth config (`static` or `oauth2`) |

**streamable-http** — Connect to MCP servers using Streamable HTTP transport.

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"streamable-http"` |
| `url` | Yes | Streamable HTTP endpoint URL |
| `headers` | No | Extra HTTP headers |
| `auth` | No | Outgoing auth config (`static` or `oauth2`) |

> Streamable HTTP backends must always set `type: streamable-http` explicitly.

### Common Backend Options

All backend types also support:

| Field | Default | Description |
|-------|---------|-------------|
| `group` | `"default"` | Logical server group name |
| `filters` | — | Per-capability allow/deny lists (tools, resources, prompts) |
| `tool_overrides` | — | Rename or override descriptions for individual tools |
| `timeouts` | — | Per-backend timeout overrides (`init`, `cap_fetch`, `sse_startup`) |

### Environment Variable Expansion

All string values support `${VAR_NAME}` syntax for environment variable expansion.

### Secret References

String values can use `secret:name` syntax to resolve values from encrypted storage (see `mcp-sentinel secret`).

## Management API

The management API is mounted at `/manage/v1/` and provides:

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/manage/v1/health` | GET | Health check (uptime, backend health summary) |
| `/manage/v1/status` | GET | Server status (version, config, endpoints, feature flags) |
| `/manage/v1/backends` | GET | List all backends with connection state and capabilities |
| `/manage/v1/groups` | GET | List logical server groups |
| `/manage/v1/capabilities` | GET | Aggregated tools, resources, prompts |
| `/manage/v1/sessions` | GET | Active MCP client sessions |
| `/manage/v1/events` | GET | Recent event log entries |
| `/manage/v1/events/stream` | GET | Live SSE event stream |
| `/manage/v1/reload` | POST | Hot-reload configuration |
| `/manage/v1/reconnect/{name}` | POST | Reconnect a specific backend |
| `/manage/v1/shutdown` | POST | Graceful server shutdown |

When `SENTINEL_MGMT_TOKEN` is set, include `Authorization: Bearer <token>` in requests.
