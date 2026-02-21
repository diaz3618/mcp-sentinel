# Tool Filtering (Allow/Deny Lists)

> **Status in analysis table:** "Yes" — MCP Sentinel has no tool filtering.

---

## What It Is

Tool filtering lets you control **which tools from a backend are exposed to clients**. Instead of exposing all 50 tools from a server, you can whitelist only the 5 you need, or blacklist the 3 that are dangerous.

## How ToolHive Implements It

ToolHive has a critical design distinction between **advertising** and **routing**:

- **Advertising** = what clients see in `tools/list` responses
- **Routing** = what the internal engine can call

Filtered tools are removed from **advertising** but remain in the **routing table**. This means composite workflows (DAG-based multi-step tools) can still call hidden tools internally, even though clients never see them.

The filter config supports:
- `allowList` — only these tools are advertised (whitelist)
- `denyList` — all tools except these are advertised (blacklist)
- `excludeAll` — hide all tools from a backend (but keep them routable for composite tools)

## How This Improves MCP Sentinel

Real-world scenarios where filtering is essential:

1. **Security**: A database server exposes `drop_table` and `query`. You only want to expose `query`.
2. **Noise reduction**: A server exposes 100 tools but users only need 10. LLMs perform better with fewer tool definitions.
3. **Multi-tenant**: Different configurations expose different tool subsets based on the deployment context.
4. **Progressive rollout**: New tools can be hidden until they're validated.

## Config Example

```json
{
  "mcpServers": {
    "database-server": {
      "url": "...",
      "tools_filter": {
        "mode": "allow",
        "names": ["query", "list_tables", "describe_table"]
      }
    },
    "risky-server": {
      "url": "...",
      "tools_filter": {
        "mode": "deny",
        "names": ["delete_all", "drop_table", "reset_database"]
      }
    }
  }
}
```

## Implementation Notes

The filter should be applied in `capability_registry.py` during `_discover_caps_by_type()`, after fetching capabilities from the backend but before adding them to the aggregated list. This is a straightforward list membership check.
