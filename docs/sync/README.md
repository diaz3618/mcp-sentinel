# Config Sync — Hot-Reload and Change Detection

Config Sync watches the configuration file for changes and automatically
reloads backends, middleware, and the tool catalog without restarting the
server.  This enables zero-downtime configuration updates.

---

## Current Implementation Status

| Component | File | Status |
|---|---|---|
| `ConfigWatcher` | `mcp_sentinel/config/watcher.py` | **Implemented** — poll-based async file watcher with debounce |
| `SentinelService` integration | `mcp_sentinel/runtime/service.py` | **Implemented** — watcher started after service reaches RUNNING state |
| `SyncStatusWidget` (TUI) | `mcp_sentinel/tui/widgets/sync_status.py` | **UI only** — renders status line + event log table, but no data flows to it |
| `SyncConfigPanel` (TUI) | `mcp_sentinel/tui/widgets/sync_status.py` | **UI only** — settings form (interval, detection method, failure mode) with no persistence |
| Config schema fields | — | **NOT WIRED** — no `sync:` section in `SentinelConfig` |

**Summary**: The backend watcher logic is solid and production-ready.  Two
gaps remain: configuration schema integration and TUI data binding.

---

## How It Works

### Poll-Based Detection

The `ConfigWatcher` uses `os.stat()` polling with a configurable interval
(default: 2 seconds).  When the file's modification time changes:

1. A **debounce window** (default: 1 second) opens to collapse rapid
   saves from editors that perform multiple writes.
2. After the debounce period, if no further changes are detected, the
   `on_change` async callback fires.
3. The callback triggers `SentinelService.reload()`, which re-reads the
   config, reconciles backend connections, and rebuilds the tool catalog.

```
os.stat(config.yaml)
  │
  ├─ mtime unchanged → sleep → poll again
  │
  └─ mtime changed → debounce (1s) → on_change() → service.reload()
```

### Detection Methods

The current implementation uses **mtime** comparison.  The TUI settings
panel shows three options that represent the planned detection spectrum:

| Method | Description | Overhead |
|---|---|---|
| **mtime** | Compare `os.stat().st_mtime` (current implementation) | Minimal |
| **hash** | SHA-256 of file contents — catches changes even if mtime is unreliable (NFS) | Low |
| **inotify** | OS-level file event notifications (Linux `inotify`, macOS `FSEvents`) | Near-zero |

For most deployments, mtime is sufficient.  Hash-based detection is
recommended for network file systems.  Inotify support would require the
`watchdog` library.

### Debounce and Failure Handling

| Scenario | Behavior |
|---|---|
| Rapid successive edits | Debounce collapses them — only one reload fires |
| Reload callback raises an exception | Error is logged, watcher continues polling |
| Config file temporarily missing | Stat returns `0.0` — treated as "no change" |

---

## What Needs to Be Done

### 1. Add `sync` section to `SentinelConfig`

```python
class SyncSettings(BaseModel):
    enabled: bool = True
    poll_interval: float = 2.0    # seconds
    debounce: float = 1.0         # seconds
    detection: str = "mtime"      # "mtime", "hash", "inotify"
    on_failure: str = "backoff"   # "backoff", "fixed", "stop"
```

### 2. Wire config values into `ConfigWatcher`

In the service startup, read `sync.poll_interval` and `sync.debounce`
from the loaded config instead of using hard-coded defaults.

### 3. Feed events to the TUI

When a change is detected (or not), push a sync event dict to
`SyncStatusWidget.add_sync_event()`:

```python
{
    "time": "14:32:05",
    "type": "changed",      # or "no-change", "error"
    "details": "3 backends reloaded"
}
```

### 4. Persist `SyncConfigPanel` settings

Wire the settings form's checkbox/select/input values to the config file
(or a settings store) so changes survive restarts.

---

## Config Example

```yaml
sync:
  enabled: true
  poll_interval: 2.0
  debounce: 1.0
  detection: mtime
  on_failure: backoff
```
