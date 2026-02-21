# Optimizer (find_tool / call_tool Meta-Tools)

> **Status in analysis table:** "Yes" — MCP Sentinel has no optimizer.

---

## What It Is

The optimizer addresses the **tool explosion problem**. When MCP Sentinel aggregates 10 servers with 20 tools each, it exposes 200 tools to the LLM. Most LLMs degrade significantly with more than ~30 tool definitions in context.

The optimizer replaces 200 tool definitions with exactly **two meta-tools**:

1. **`find_tool(query, limit)`** — Semantic search across all tool names and descriptions. Returns the top-N matching tool definitions.
2. **`call_tool(name, args)`** — Dynamic invocation. Routes the call to the correct backend.

## How ToolHive Implements It

ToolHive's `pkg/vmcp/optimizer/` package:

### Tool Store
- `InMemoryToolStore` — Simple list scan for small deployments
- `SQLiteToolStore` — Uses SQLite FTS5 (full-text search) for larger deployments
- Both implement `ToolStore` interface: `Store(tools)`, `Search(query, limit)`, `Get(name)`

### find_tool
```
Input:  { "query": "search for GitHub issues", "limit": 5 }
Output: [
  { "name": "github_search_issues", "description": "...", "schema": {...} },
  { "name": "jira_search", "description": "...", "schema": {...} },
  ...
]
```

The LLM gets full tool definitions only for relevant matches, not the entire catalog.

### call_tool  
```
Input:  { "name": "github_search_issues", "arguments": { "query": "bug", "state": "open" } }
Output: { "result": [...] }
```

Routes through the normal routing table to the correct backend.

### Token Savings Metrics
ToolHive tracks baseline token count (all tools) vs. actual tokens returned, reporting savings percentage.

## How This Improves MCP Sentinel

| Without Optimizer | With Optimizer |
|----------|---------|
| 200 tool definitions in every LLM prompt | 2 meta-tool definitions |
| ~40,000 tokens of tool schemas | ~500 tokens of meta-tool schemas |
| LLM struggles to pick the right tool | LLM searches first, then calls |
| Every API call includes full catalog | Only relevant tools are fetched |

The token savings alone justify the feature for any deployment with more than ~20 tools.

## Implementation Path

```python
# In-memory implementation (sufficient for most deployments)
class ToolIndex:
    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def store(self, tools: list[ToolDef]) -> None:
        for t in tools:
            self._tools[t.name] = t

    def search(self, query: str, limit: int = 10) -> list[ToolDef]:
        query_lower = query.lower()
        scored = []
        for t in self._tools.values():
            text = f"{t.name} {t.description}".lower()
            score = sum(1 for word in query_lower.split() if word in text)
            if score > 0:
                scored.append((score, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]
```

The optimizer is toggled per-config and, when enabled, replaces the normal `tools/list` response with the two meta-tools.

**Estimated effort:** Medium — the indexing is straightforward. The routing already exists in the forwarder.
