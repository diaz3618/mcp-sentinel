# Service Lifecycle

The `SentinelService` class orchestrates the entire runtime: loading config,
managing backend connections, and coordinating subsystems.

## SentinelService

`mcp_sentinel/runtime/service.py` is the central orchestrator.

### Startup (`service.start(config_path)`)

```
1. Load and validate config file
2. Resolve secret:name references via SecretStore
3. Initialize ClientManager with backend configs
4. Start all backend connections (parallel)
5. Build CapabilityRegistry from connected backends
6. Apply conflict resolution, filters, renames
7. Initialize subsystems:
   - AuditLogger (if enabled)
   - HealthChecker
   - GroupManager
   - ToolIndex (if optimizer enabled)
   - FeatureFlags
8. Report status via console/display
```

### Shutdown (`service.stop()`)

```
1. Stop health checker
2. Disconnect all backends gracefully
3. Close audit logger
4. Clean up resources
```

### Hot-Reload (`service.reload()`)

```
1. Re-read config file
2. Diff against current config
3. Stop removed backends
4. Start added backends
5. Reconnect changed backends
6. Rebuild capability registry
7. Report changes
```

### Reconnect (`service.reconnect(backend_name)`)

Reconnects a single backend without affecting others. Useful for recovering
from transient failures.

## Runtime Models

`mcp_sentinel/runtime/models.py` defines status models:

### BackendPhase

Six-phase lifecycle enum tracking each backend's state:

| Phase | Description |
|-------|-------------|
| `PENDING` | Configured, not started |
| `INITIALIZING` | Connection in progress |
| `READY` | Connected, serving capabilities |
| `DEGRADED` | Health check failing but connected |
| `FAILED` | Connection error |
| `SHUTTING_DOWN` | Disconnecting |

### BackendCondition

Structured status conditions attached to each backend:

```python
BackendCondition(
    type="Ready",
    status=True,
    reason="Connected",
    message="Backend initialized successfully",
    last_transition="2026-02-23T12:00:00Z"
)
```

### BackendStatusRecord

Combines phase, conditions, and metadata for each backend. Tracks last
transition time and phase history.

## Subsystem Integration

The service coordinates these subsystems:

| Subsystem | Module | Role |
|-----------|--------|------|
| ClientManager | `bridge/client_manager.py` | Backend connections |
| CapabilityRegistry | `bridge/capability_registry.py` | Capability aggregation |
| AuditLogger | `audit/logger.py` | Audit event recording |
| HealthChecker | `bridge/health/` | Backend health monitoring |
| GroupManager | `bridge/groups.py` | Logical server groups |
| ToolIndex | `bridge/optimizer/` | Tool search index |
| SessionManager | `server/session/` | Client session tracking |
| FeatureFlags | `config/flags.py` | Feature toggles |
| SkillManager | `skills/manager.py` | Skill pack management |
| SecretStore | `secrets/store.py` | Encrypted secret access |
