# Tool Renaming / Description Override

> **Status in analysis table:** "Yes" — MCP Sentinel has no tool renaming.

---

## What It Is

Tool renaming lets operators **alias tool names and override descriptions** without modifying the backend MCP server. This is useful when:

- A tool's name is ambiguous without its server context (e.g., `search` → `github_search`)
- A tool's description is poor or misleading
- You want consistent naming conventions across servers from different vendors
- An LLM needs better descriptions to select the right tool

## How ToolHive Implements It

ToolHive's aggregator has a `tool_adapter.go` component that applies two mappings:

1. **Name renames** — A map of `{original_name → new_name}` applied before conflict resolution
2. **Description overrides** — A map of `{tool_name → new_description}` applied to the tool's JSON schema

The adapter modifies the tool definition in the routing table so:
- Clients see the **renamed** tool in `tools/list`
- When clients call the renamed tool, the router maps it back to the **original name** before forwarding to the backend

This means the backend server doesn't need to know about any renaming.

## How This Improves MCP Sentinel

Without renaming:
- Tools from different servers may have confusing or duplicate names
- Users cannot customize tool descriptions for their specific LLM
- Poor descriptions from upstream servers degrade tool selection accuracy

With renaming:
- Operators can present a clean, consistent tool catalog
- Descriptions can be tuned per-deployment for specific LLM models
- Combined with conflict resolution, every tool can have a unique, meaningful name

## Config Example

```json
{
  "mcpServers": {
    "my-server": {
      "tool_overrides": {
        "search": {
          "name": "database_search",
          "description": "Search the PostgreSQL database by natural language query. Returns up to 50 matching rows."
        },
        "execute": {
          "name": "db_execute",
          "description": "Execute a raw SQL statement against the PostgreSQL database."
        }
      }
    }
  }
}
```

## Implementation Notes

Apply overrides in `capability_registry.py` during `_discover_caps_by_type()`:
1. Fetch raw tool list from backend
2. Apply name renames (mutate the tool name in the definition)
3. Apply description overrides (mutate the description field)
4. Build a reverse mapping (`new_name → original_name`) for the forwarder
5. Then proceed with conflict resolution

The reverse mapping is critical — when a client calls `database_search`, the forwarder needs to send `search` to the backend.
