# Conflict Resolution Strategies

> **Status in analysis table:** "Yes" — This is a gap. MCP Sentinel currently uses first-wins only.

---

## What It Is

When MCP Sentinel aggregates tools from multiple backend servers, **name collisions happen**. If two backends both expose a tool called `search`, which one should clients see?

Today, MCP Sentinel silently ignores duplicates (first-wins). ToolHive offers three configurable strategies.

## How ToolHive Implements It

ToolHive's `pkg/vmcp/aggregator/` package implements a three-stage pipeline: **Query → Resolve → Merge**.

The conflict resolution step runs three possible resolvers:

### 1. Prefix Strategy (`prefix_resolver.go`)
Renames **every** tool to `{backend_name}_{tool_name}`. No conflicts possible.

- Example: Two servers both have `search` → becomes `github_search` and `jira_search`
- A configurable separator (default `_`) controls the format
- The routing table maps the prefixed name back to the original name when forwarding calls

### 2. Priority Strategy (`priority_resolver.go`)
Backends are ranked by a user-defined priority list. For duplicate names, the highest-priority backend wins.

- Backends not in the priority list fall back to the prefix strategy (preventing silent data loss)
- Example: priority `["primary-server", "backup-server"]` — if both have `search`, primary wins

### 3. Manual Strategy (`manual_resolver.go`)
Every conflict must be explicitly resolved in the config file. If any conflict is unresolved, **startup fails**.

- Supports both name overrides and description overrides
- Forces the operator to make deliberate choices about every collision
- Safest strategy for production deployments

## How This Improves MCP Sentinel

Without conflict resolution, MCP Sentinel:
- Silently drops duplicate tools (users don't know tools are missing)
- Has no way to distinguish same-named tools from different servers
- Forces users to manually ensure no naming collisions across all backends

With configurable strategies:
- **prefix** mode: Zero-config, every tool is accessible, names are unambiguous
- **priority** mode: Power users can control which server "wins" for each conflict
- **manual** mode: Production deployments can audit exactly which tools are exposed

## Config Example

```json
{
  "conflict_resolution": {
    "strategy": "prefix",
    "separator": "_"
  }
}
```

Or with priority:

```json
{
  "conflict_resolution": {
    "strategy": "priority",
    "order": ["primary-server", "tools-server", "utils-server"]
  }
}
```
