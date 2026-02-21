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