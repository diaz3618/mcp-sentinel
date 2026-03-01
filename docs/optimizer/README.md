# Optimizer — find_tool / call_tool Meta-Tools

The Optimizer replaces the full tool catalog with two meta-tools —
`find_tool` and `call_tool` — to reduce token consumption and improve
LLM tool selection when a server exposes hundreds or thousands of tools.

---

## Current Implementation Status

| Component | File | Status |
|---|---|---|
| `OptimizerConfig` | `argus_mcp/config/schema.py` | **Implemented** — `enabled: bool`, `keep_tools: List[str]` |
| `ToolIndex` (TF-IDF + fallback) | `argus_mcp/bridge/optimizer/search.py` | **Implemented** — scikit-learn TF-IDF cosine similarity with word-overlap fallback |
| Meta-tool definitions | `argus_mcp/bridge/optimizer/meta_tools.py` | **Implemented** — `find_tool` and `call_tool` MCP Tool definitions |
| Server wiring | `argus_mcp/server/lifespan.py` | **Implemented** — reads config, builds ToolIndex, attaches to mcp_server |
| Handler integration | `argus_mcp/server/handlers.py` | **Implemented** — `list_tools` returns meta-tools + keep-list; `call_tool` dispatches to real backend |
| TUI panel | `argus_mcp/tui/widgets/optimizer_panel.py` | **Partially wired** — status display and test search work, but test search uses naive substring matching instead of the real ToolIndex |

**Summary**: The Optimizer is the most complete feature.  The only gaps are
TUI test search using the real index and populating the token savings display
with actual data.

---

## How It Works

### The Problem

When an MCP server aggregates tools from many backends, the `list_tools`
response can contain hundreds of tool definitions.  Sending all of them to
an LLM in every request:

- Wastes **tokens** (tool schemas are verbose JSON)
- Confuses the LLM (too many choices → worse tool selection)
- Increases **latency** (larger prompts = slower inference)

### The Solution

With the Optimizer enabled, `list_tools` returns only:

| Tool | Purpose |
|---|---|
| `find_tool(query, limit)` | Semantic search across the full tool catalog |
| `call_tool(name, arguments)` | Invoke any tool by exact name |

Plus any tools listed in `keep_tools` (tools the LLM should always see).

The LLM workflow becomes:

```
1. LLM calls find_tool("send email", limit=3)
2. Argus MCP searches the ToolIndex, returns top 3 matches
3. LLM picks the best match, calls call_tool("gmail.send", {to: ..., body: ...})
4. Argus MCP dispatches to the real backend
```

### Token Savings

| Scenario | Baseline Tokens | Optimized Tokens | Savings |
|---|---|---|---|
| 50 tools | ~12,500 | ~1,200 | **~90%** |
| 200 tools | ~50,000 | ~1,200 | **~97%** |
| 500 tools | ~125,000 | ~1,200 | **~99%** |

The optimized token count is roughly constant regardless of catalog size
(2 meta-tool schemas ≈ 600 tokens + keep-list tools).

---

## Search Index

The `ToolIndex` supports two scoring backends:

### TF-IDF + Cosine Similarity (scikit-learn)

When `scikit-learn` is installed, the index builds a TF-IDF matrix from
tool names and descriptions, then computes cosine similarity between the
query vector and the document matrix.

**Pros**: High-quality semantic matching, handles multi-word queries well.

**Cons**: Requires scikit-learn (~30 MB dependency).

### Word-Overlap Fallback

When scikit-learn is not installed, the index falls back to a simple scorer:

- Exact token match → 1.0 weight
- Partial substring match → 0.5 weight
- Contained in document text → 0.25 weight

Normalized by query token count.  Good enough for most catalogs.

---

## Configuration

```yaml
optimizer:
  enabled: true
  keep_tools:
    - essential-tool-1
    - essential-tool-2
```

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Master switch for the optimizer |
| `keep_tools` | list of strings | `[]` | Tool names to always expose alongside meta-tools |

The `keep_tools` list is for tools the LLM must always have access to
without needing to search first (e.g., a conversation tool, a help tool).

---

## Meta-Tool Definitions

### `find_tool`

```json
{
  "name": "find_tool",
  "description": "Search across all available tools by keyword or description. Returns the top matching tool definitions with their schemas. Use this first to discover relevant tools before calling them.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query — keywords matching tool names or descriptions."
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of results to return (default: 5).",
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

### `call_tool`

```json
{
  "name": "call_tool",
  "description": "Call any tool by its exact name with the given arguments. Use find_tool first to discover the tool name and required arguments.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "The exact name of the tool to call."
      },
      "arguments": {
        "type": "object",
        "description": "Arguments to pass to the tool.",
        "default": {}
      }
    },
    "required": ["name"]
  }
}
```

---

## TUI Integration

The **Operations → Optimizer** tab displays:

- **Status**: Enabled/disabled, tool count, index backend (sklearn or fallback)
- **Token Savings**: Progress bar showing estimated token reduction
- **Meta-Tools**: Description of `find_tool` and `call_tool`
- **Test Search**: Input field + results table for testing queries against the index

---

## What Needs to Be Done

### 1. Wire TUI test search to real `ToolIndex`

The current test search in `optimizer_panel.py` does naive substring matching
against cached capabilities.  It should instead call the actual `ToolIndex`
attached to the server instance.

### 2. Populate token savings with real data

The token savings progress bar is currently static.  It should calculate:

- **Baseline**: `total_tools × avg_schema_tokens`
- **Optimized**: `2 (meta-tools) + len(keep_tools) × avg_schema_tokens`

### 3. Optional: SQLite FTS5 backend

For very large catalogs (1000+ tools), consider adding a persistent
SQLite FTS5 index as an alternative to in-memory TF-IDF.
