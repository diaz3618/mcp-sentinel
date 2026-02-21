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