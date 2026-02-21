# Additional Features Discovered in ToolHive Repos

> Features found by deep-inspecting `toolhive`, `toolhive-cloud-ui`, `toolhive-registry-server`, and `toolhive-studio` that are **not covered** in the original comparison table.

---

## Table of Contents

1. [AI Chat Playground](#1-ai-chat-playground)
2. [Tool Customization UI](#2-tool-customization-ui)
3. [MCP Optimizer as Meta-MCP](#3-mcp-optimizer-as-meta-mcp)
4. [Feature Flags System](#4-feature-flags-system)
5. [Version Drift Detection](#5-version-drift-detection)
6. [Graceful Exit with Resume](#6-graceful-exit-with-resume)
7. [Composable Polling Engine](#7-composable-polling-engine)
8. [Skills System](#8-skills-system)
9. [Network Isolation Configuration](#9-network-isolation-configuration)
10. [CLI Alignment Validation](#10-cli-alignment-validation)
11. [Server Catalog with Grid/List Toggle](#11-server-catalog-with-gridlist-toggle)
12. [Conversation Persistence](#12-conversation-persistence)
13. [Elicitation Protocol Support](#13-elicitation-protocol-support)
14. [Multiple Registry Sources](#14-multiple-registry-sources)
15. [Background Sync with Change Detection](#15-background-sync-with-change-detection)

---

## 1. AI Chat Playground

**Source:** `toolhive-cloud-ui`, `toolhive-studio`

Both the Cloud UI and Studio include a built-in AI chat interface that uses MCP tools:

### Cloud UI Implementation
- **LLM Provider:** OpenRouter (access to 100+ models)
- **Streaming:** Real-time markdown rendering via `@ai-sdk/react`
- **Conversation Persistence:** IndexedDB via Dexie (survives page reload)
- **Tool Call Visualization:** Expandable cards showing tool name, input args, output
- **MCP Integration:** Connects to servers via SSE/StreamableHTTP, per-tool enable/disable UI
- **Model Selector:** Dropdown with model ID, name, pricing info

### Studio Implementation
- **7 LLM Providers:** OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama, LM Studio
- **Threading:** Multiple conversation threads with history
- **MCP Server Selector:** Choose which running servers to include in the conversation
- **Per-tool Toggle:** Enable/disable individual tools per conversation
- **Streaming:** Token-by-token response rendering

### Relevance to MCP Sentinel
A TUI-based chat playground would let users **test MCP tools without needing an external AI client**. Textual's `RichLog` widget can render streaming markdown. This is a unique selling point — no other TUI aggregator offers built-in tool testing.

**Effort:** High — requires LLM API integration, streaming rendering, conversation state management.  
**Priority:** P3 — nice-to-have but significant differentiation.

---

## 2. Tool Customization UI

**Source:** `toolhive-studio`

Studio provides a **visual tool editor** for each server:

- **Enable/Disable Toggle:** Per-tool switches (affects which tools are advertised)
- **Description Override:** Edit tool descriptions inline
- **Diff View:** Compare customized description vs. original registry description
- **Reset:** Revert individual overrides back to original

This is more granular than tool filtering — it's a full UI for fine-tuning the tool catalog.

### Relevance to MCP Sentinel
The TUI could offer a tool customization screen:
```
┌─── Tool Customization: github-server ──────────────────┐
│                                                        │
│ Tool              Enabled  Description (customized)    │
│ ────────────────────────────────────────────────────── │
│ search_issues     [✓]      Search GitHub issues by...  │
│ create_issue      [✓]      Create a new GitHub issue   │
│ delete_repo       [ ]      ⚠ Disabled (destructive)   │
│ list_repos        [✓]      (original description)      │
│                                                        │
│ [Tab] Toggle  [E] Edit Description  [R] Reset  [S] Save│
└────────────────────────────────────────────────────────┘
```

**Effort:** Medium — combines tool filtering + renaming with a TUI form.  
**Priority:** P2 — after tool filtering and renaming are implemented.

---

## 3. MCP Optimizer as Meta-MCP

**Source:** `toolhive` (`pkg/vmcp/optimizer/`)

Beyond the `find_tool`/`call_tool` optimization (covered in the analysis), the optimizer is architecturally interesting because it's a **meta-MCP server** — an MCP server that manages other MCP tools.

Key detail not in the original analysis:
- **Token usage tracking:** Compares baseline token count (all tool definitions) vs. actual tokens returned via `find_tool`, reporting savings percentage
- **SQLite FTS5 backend:** For larger deployments, tool search uses SQLite full-text search with BM25 ranking
- **Configurable threshold:** Optimizer only activates when tool count exceeds a threshold (e.g., 30 tools)

### Relevance to MCP Sentinel
The auto-activation threshold is particularly useful — for small deployments (5-10 tools), the optimizer adds unnecessary indirection. The threshold ensures it only kicks in when it actually helps.

```json
{
  "optimizer": {
    "enabled": true,
    "activation_threshold": 30,
    "max_results": 10,
    "backend": "memory"
  }
}
```

---

## 4. Feature Flags System

**Source:** `toolhive-studio`

Studio implements a **centralized feature flag system**:

- **Centralized keys:** All flags defined in a single enum/registry
- **Electron-store persistence:** Flags saved per-user in the app's data directory
- **Experimental features toggle:** Settings UI has an "Experimental Features" section
- **Progressive rollout:** New features launch behind flags, enabled by power users
- **Default-off:** All experimental flags default to disabled

Feature flags in Studio:
```typescript
export const FEATURE_FLAGS = {
  AI_CHAT: 'ai-chat',
  TOOL_CUSTOMIZATION: 'tool-customization',
  OPTIMIZER: 'optimizer',
  SERVER_GROUPS: 'server-groups',
  // ...
} as const;
```

### Relevance to MCP Sentinel
As MCP Sentinel grows features, a flag system prevents feature bloat and lets users opt into experimental functionality:

```json
{
  "features": {
    "optimizer": false,
    "composite_workflows": false,
    "health_checks": true,
    "audit_logging": true
  }
}
```

**Effort:** Low — simple config-based flag checking.  
**Priority:** P2 — implement when there are enough features to warrant gating.

---

## 5. Version Drift Detection

**Source:** `toolhive-studio`

Studio compares **local server versions against the registry** and alerts when updates are available:

- Periodic check against registry API
- Badge on server card: "Update available: v2.1.0 → v3.0.0"
- One-click update button
- Changelog display for new versions

### Relevance to MCP Sentinel
If MCP Sentinel integrates with a registry, version drift detection becomes a natural extension:
- TUI notification: "github-mcp has an update: v2.1.0 → v3.0.0"
- Useful for stdio servers installed via `pip` or `npm`(could check PyPI/npm APIs)

**Effort:** Medium — requires registry integration + version comparison logic.  
**Priority:** P3 — depends on registry support.

---

## 6. Graceful Exit with Resume

**Source:** `toolhive-studio`

Studio tracks which servers are running at exit and **automatically restarts them on next launch**:

- On shutdown: Save list of running servers to persistent storage
- On startup: Read saved list, automatically start those servers
- Recovery: If a server fails to restart, log warning but continue with others
- User control: "Start on launch" toggle per server

### Relevance to MCP Sentinel
MCP Sentinel could persist its connection state:
- On exit: Save `config.json` with a `"last_running"` field
- On startup: Automatically connect to previously-running backends
- This is especially useful for stdio backends that need to be launched as subprocesses

**Effort:** Low — serialize/deserialize a server name list.  
**Priority:** P3 — quality of life improvement.

---

## 7. Composable Polling Engine

**Source:** `toolhive-studio`

Studio's polling engine is a reusable abstraction for monitoring async processes:

```typescript
function createPoller(config: {
  fn: () => Promise<Result>,
  interval: number,
  condition: (result: Result) => boolean,
  onMatch: (result: Result) => void,
  timeout?: number,
}): Poller
```

Key patterns:
- **`pollServerUntilStable`** — Polls server status, resolves when status stops changing for N consecutive checks
- **Transition detection** — Detects when a server moves from one state to another
- **Auto-resume** — If polling detects an unexpected transition, extends the polling window
- **Optimistic updates** — UI updates immediately with expected state, polling confirms

### Relevance to MCP Sentinel
The polling pattern maps to health checks. Instead of a simple `check every 30s`, a smarter poller could:
- Poll frequently during state transitions (e.g., when a backend is reconnecting)
- Slow down when everything is stable
- Detect and report state transitions (not just current state)

**Effort:** Low — the pattern is straightforward with `asyncio`.  
**Priority:** P1 — should be part of health check implementation.

---

## 8. Skills System

**Source:** `toolhive-registry-server`

Beyond raw MCP servers, the registry supports a **skills API**:

- Skills represent higher-level capabilities (e.g., "code review", "data analysis")
- Each skill links to one or more MCP servers/tools
- Skills have their own CRUD API
- Skills can reference OCI containers or Git repositories
- Tagged and searchable independently from raw tool names

### Relevance to MCP Sentinel
Skills could serve as a **curated preset system** — instead of configuring individual tools, users select a skill ("code review") and MCP Sentinel automatically configures the right servers and tools.

**Effort:** High — requires registry integration and skill-to-server mapping.  
**Priority:** P3 — future consideration.

---

## 9. Network Isolation Configuration

**Source:** `toolhive` (`pkg/labels/`, container configs)

ToolHive configures **per-server network isolation** via container labels:

- `network.mode`: `host`, `bridge`, `none`
- `network.allow`: Specific hostnames/IPs the server can reach
- Per-server firewall rules
- DNS isolation

### Relevance to MCP Sentinel
For stdio backends (subprocesses), network isolation could be achieved via:
- Environment variable whitelisting (`HTTP_PROXY`, `NO_PROXY`)
- Systemd socket activation with network namespaces (Linux)
- macOS sandbox profiles

This is niche but relevant for security-sensitive deployments.

**Effort:** High — OS-specific sandboxing.  
**Priority:** P3+ — only for security-hardened deployments.

---

## 10. CLI Alignment Validation

**Source:** `toolhive-studio`

Studio validates that its **bundled `thv` CLI binary matches the expected version**:

- On startup: Run `thv --version` and compare against expected
- Version mismatch: Show warning banner with update instructions
- Missing CLI: Show setup instructions
- Auto-download: Option to automatically fetch the correct CLI version

### Relevance to MCP Sentinel
If MCP Sentinel has a CLI mode alongside the TUI, version validation ensures consistency. More broadly, this pattern applies to validating that required external tools (Python, Node.js, `uvx`, `npx`) are available at the expected versions.

**Effort:** Low — subprocess version check.  
**Priority:** P3 — minor quality-of-life.

---

## 11. Server Catalog with Grid/List Toggle

**Source:** `toolhive-cloud-ui`

The server catalog offers two view modes persisted in the URL:

- **Grid view**: Card-based layout with icon, name, description, badges
- **List view**: Compact table with sortable columns
- Toggle via button, state persisted in URL query params (via `nuqs`)
- Both views share the same search/filter state

### Relevance to MCP Sentinel
The TUI equivalent: a toggle between compact and expanded backend views:
- **Compact**: One line per server: `● github-server [healthy] 12 tools 142ms`
- **Expanded**: Multi-line with tool list, error details, conditions history

Textual's `ContentSwitcher` can swap between these views on a keybinding.

**Effort:** Low — two widget layouts with a switcher.  
**Priority:** P2 — UX improvement.

---

## 12. Conversation Persistence

**Source:** `toolhive-cloud-ui` (IndexedDB via Dexie), `toolhive-studio` (file-based)

Both apps persist AI chat conversations across sessions:
- Cloud UI: IndexedDB with Dexie ORM, per-conversation threads
- Studio: File-based storage, conversation threads with metadata

### Relevance to MCP Sentinel
If an AI chat playground is added, conversation persistence would use SQLite or JSON files. Low priority without the chat feature.

**Effort:** Medium (only relevant if chat playground is built).  
**Priority:** P3+.

---

## 13. Elicitation Protocol Support

**Source:** `toolhive` (`pkg/vmcp/composer/`)

MCP's **elicitation protocol** allows tools to request human input during execution:
- A workflow step can pause and present a question to the user
- The user provides input via the MCP client
- The workflow resumes with the user's answer

### Relevance to MCP Sentinel
Elicitation support makes composite workflows interactive. The TUI is an ideal surface for this — a modal dialog asking the user for input before the workflow continues.

**Effort:** Medium — requires MCP elicitation message handling.  
**Priority:** P3 — depends on composite workflows.

---

## 14. Multiple Registry Sources

**Source:** `toolhive-registry-server`

The registry server can ingest from **5 different data source types simultaneously**:
- Git repositories (YAML/JSON manifests)
- Other registry APIs (federation)
- Local filesystem directories
- Managed entries (direct API publish)
- Kubernetes CRDs

Each source type has a `RegistryHandler` that implements `Fetch()` → `[]ServerEntry`.

### Relevance to MCP Sentinel
Supporting multiple registry sources means users can combine public registries with private ones. The registry client in MCP Sentinel could support a list of registries with priority ordering.

**Effort:** Low (in registry client) — just iterate over configured registry URLs.  
**Priority:** P2 — alongside registry support.

---

## 15. Background Sync with Change Detection

**Source:** `toolhive-registry-server`

The sync coordinator:
- Runs every 2 minutes with random jitter (prevents thundering herd)
- Computes content hash before and after fetch
- Only processes changes if hash differs (saves CPU/IO)
- Exponential backoff on failures per source

### Relevance to MCP Sentinel
This pattern applies to **config hot-reload**:
- Watch `config.json`/`config.yaml` for changes
- Compute hash before and after
- Only reload if content actually changed
- Reconnect to new/changed backends, disconnect removed ones

**Effort:** Low — file watcher + hash comparison.  
**Priority:** P2 — very convenient for development workflows.
