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