# Config Format & Validation

> **Status in analysis table:** "Yes" — MCP Sentinel uses JSON with minimal validation.

---

## What It Is

Config format improvements cover two areas:
1. **YAML support** — Human-friendly config syntax with comments and multi-line strings
2. **Schema validation** — Catch config errors at startup instead of at runtime

## How ToolHive Implements It

### YAML with Full Schema
ToolHive uses YAML configuration with:
- JSON Schema validation at startup
- Per-workload overrides (backends can override global settings)
- Custom duration type (`"30s"`, `"5m"`) instead of raw seconds
- Versioned config format with migration support
- `PartialFailureMode` enum (`"fail"` vs `"continue"`) for controlling behavior when some backends fail

### Config Export/Import (RunConfig)
ToolHive Studio exports server configurations as portable `RunConfig` objects:
- Includes server definition, environment variables, secrets references
- Can be imported on another machine
- Used for "share my setup" workflows

## Current State in MCP Sentinel

```json
{
  "mcpServers": {
    "server-a": {
      "command": "python",
      "args": ["-m", "mcp_server_a"]
    }
  }
}
```

Problems:
- No comments allowed in JSON (can't explain why settings are what they are)
- No validation — typos in field names are silently ignored
- No default values — every field must be explicitly set
- No per-server timeout overrides
- No documentation of available fields

## How This Improves MCP Sentinel

### YAML Support
```yaml
# MCP Sentinel Configuration
# See docs/config.md for full reference

# Global timeouts (can be overridden per-server)
timeouts:
  init: 15s
  capability_fetch: 10s
  tool_call: 30s

# Conflict resolution for duplicate tool names
conflict_resolution:
  strategy: prefix
  separator: "_"

# Backend MCP servers
mcpServers:
  # Local development server
  dev-tools:
    command: python
    args: ["-m", "my_mcp_server"]
    timeouts:
      tool_call: 60s  # This server is slow
    tools_filter:
      mode: allow
      names: [search, query]

  # Production API server  
  prod-api:
    transport: sse
    url: https://api.example.com/mcp/sse
    headers:
      Authorization: "Bearer $API_TOKEN"
```

### Schema Validation

```python
from pydantic import BaseModel, Field
from typing import Literal

class TimeoutConfig(BaseModel):
    init: float = Field(default=15.0, description="Seconds to wait for MCP init")
    capability_fetch: float = Field(default=10.0)
    tool_call: float = Field(default=30.0)

class ToolsFilter(BaseModel):
    mode: Literal["allow", "deny"]
    names: list[str]

class ServerConfig(BaseModel):
    command: str | None = None
    args: list[str] = []
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    url: str | None = None
    headers: dict[str, str] = {}
    timeouts: TimeoutConfig | None = None
    tools_filter: ToolsFilter | None = None
    tool_overrides: dict[str, dict] = {}

class SentinelConfig(BaseModel):
    mcpServers: dict[str, ServerConfig]
    timeouts: TimeoutConfig = TimeoutConfig()
    conflict_resolution: dict = {"strategy": "first_wins"}
```

With Pydantic:
- Typos are caught immediately: `"comand"` raises `ValidationError`
- Type mismatches are caught: `"timeout": "ten"` → error
- Missing required fields are caught
- Default values are applied automatically
- Schema can be exported as JSON Schema for editor autocomplete

## Implementation Path

### Phase 1: Pydantic Validation (P0)
Add Pydantic models in `config_loader.py`. Validate config on load. Fail fast with clear error messages.

### Phase 2: YAML Support (P1)
```python
import yaml

def load_config(path: str) -> SentinelConfig:
    with open(path) as f:
        if path.endswith(('.yml', '.yaml')):
            raw = yaml.safe_load(f)
        else:
            raw = json.load(f)
    return SentinelConfig(**raw)
```

Add `pyyaml` to dependencies. Support both `config.json` and `config.yaml`.

### Phase 3: Config Export/Import (P2)
Export the current running config (minus secrets) as a portable file that others can import.

**Dependencies:** `pydantic` (likely already a transitive dep via `mcp` SDK), `pyyaml` (new).

**Estimated effort:** Phase 1 is Low (Pydantic models). Phase 2 is Low (YAML loader). Phase 3 is Medium.
