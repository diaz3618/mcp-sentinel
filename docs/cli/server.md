# `mcp-sentinel server`

Start the headless Sentinel gateway server.

## Usage

```bash
mcp-sentinel server [--host HOST] [--port PORT] [--log-level LEVEL] [--config PATH]
```

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--host` | string | `127.0.0.1` | Bind address |
| `--port` | integer | `9000` | Listen port |
| `--log-level` | string | `info` | Log level: `debug`, `info`, `warning`, `error`, `critical` |
| `--config` | path | auto-detect | Path to config file (JSON or YAML) |

## Config File Resolution

The server resolves the config file using this priority:

1. **`--config` flag** — explicit path (highest priority)
2. **`SENTINEL_CONFIG` environment variable** — path from env
3. **Auto-detection** — scans the project directory for:
   - `config.yaml`
   - `config.yml`

The first file found is used. If none exist, the server exits with an error.

## Examples

```bash
# Start with defaults (localhost:9000, auto-detect config)
mcp-sentinel server

# Custom host and port
mcp-sentinel server --host 0.0.0.0 --port 8080

# Explicit config file
mcp-sentinel server --config /etc/mcp-sentinel/production.yaml

# Debug logging
mcp-sentinel server --log-level debug

# Using environment variable
export SENTINEL_CONFIG=/path/to/config.yaml
mcp-sentinel server
```

## Server Endpoints

Once running, the server exposes:

| Endpoint | Purpose |
|----------|---------|
| `GET /sse` | SSE transport for MCP clients |
| `POST /messages/` | SSE message submission |
| `GET\|POST\|DELETE /mcp` | Streamable HTTP transport |
| `/manage/v1/*` | Management REST API |

## Management Token

To protect the management API, set a bearer token:

```yaml
# In config.yaml
server:
  management:
    token: "${SENTINEL_MGMT_TOKEN}"
```

```bash
export SENTINEL_MGMT_TOKEN=my-secret-token
mcp-sentinel server
```

The `/manage/v1/health` endpoint is always public (no token required).

## Signals

| Signal | Behavior |
|--------|----------|
| `SIGINT` (Ctrl+C) | Graceful shutdown |
| `SIGTERM` | Graceful shutdown |
