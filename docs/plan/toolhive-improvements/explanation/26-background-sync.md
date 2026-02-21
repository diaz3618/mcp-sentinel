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