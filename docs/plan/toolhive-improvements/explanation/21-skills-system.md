# Skills System

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
