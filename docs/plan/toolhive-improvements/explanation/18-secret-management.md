# Secret Management

> **Status in analysis table:** "Yes" — MCP Sentinel stores credentials in plaintext config.

---

## What It Is

Secret management provides secure storage and injection of sensitive values — API keys, tokens, passwords — without leaving them in plaintext in `config.json`.

## How ToolHive Implements It

### ToolHive Core
- **AES-256-GCM** encrypted secrets file alongside config
- **Environment variable expansion**: `$ENV_VAR` syntax in config values
- **1Password integration**: Pull secrets from 1Password vaults at runtime
- **OS keyring**: Platform keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)

### ToolHive Studio
- **Secrets management UI**: Dedicated table view for managing secrets
- **Server form integration**: Secrets can be referenced by name in server config
- **Encrypted Electron store**: Secrets encrypted at rest using `electron-store` + `safeStorage`
- **Secret reference syntax**: `{{ secrets.my_api_key }}` in server config fields

## Current State in MCP Sentinel

```json
{
  "mcpServers": {
    "api-server": {
      "url": "https://api.example.com/sse",
      "headers": {
        "Authorization": "Bearer sk-1234567890abcdef"  // ← Plaintext!
      }
    }
  }
}
```

Anyone with read access to `config.json` gets all credentials.

## How This Improves MCP Sentinel

### Without Secret Management
- API keys visible in plaintext in config files
- Config cannot be committed to version control
- No credential rotation without editing config
- No audit trail for secret access

### With Secret Management
- **Environment variable expansion**: `$API_TOKEN` replaced at config load time
- **Encrypted secrets file**: Credentials stored AES-encrypted, decrypted at runtime
- **Separation of concerns**: Config structure in `config.json`, secrets in `.secrets` or env
- **Safe version control**: Config can be committed without exposing credentials

## Implementation Path

### Phase 1: Environment Variable Expansion (Minimal, High Impact)

```python
import os
import re

def expand_env_vars(value: str) -> str:
    """Replace $ENV_VAR and ${ENV_VAR} patterns with environment variable values."""
    def replacer(match):
        var_name = match.group(1) or match.group(2)
        val = os.environ.get(var_name)
        if val is None:
            raise ValueError(f"Environment variable '{var_name}' not set")
        return val
    return re.sub(r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)', replacer, value)
```

Config becomes:
```json
{
  "mcpServers": {
    "api-server": {
      "headers": {
        "Authorization": "Bearer $API_TOKEN"
      }
    }
  }
}
```

Users set `export API_TOKEN=sk-1234567890` in their shell.

### Phase 2: Encrypted Secrets File

```python
from cryptography.fernet import Fernet

class SecretStore:
    def __init__(self, path: str, key: bytes):
        self._path = path
        self._fernet = Fernet(key)
    
    def get(self, name: str) -> str:
        data = json.loads(self._fernet.decrypt(self._path.read_bytes()))
        return data[name]
    
    def set(self, name: str, value: str):
        try:
            data = json.loads(self._fernet.decrypt(self._path.read_bytes()))
        except FileNotFoundError:
            data = {}
        data[name] = value
        self._path.write_bytes(self._fernet.encrypt(json.dumps(data).encode()))
```

Config reference syntax:
```json
{
  "headers": {
    "Authorization": "Bearer ${secret:api_token}"
  }
}
```

### Phase 3: TUI Secrets Manager
A modal screen for adding/editing/deleting secrets, showing only names (never values):

```
┌─── Secrets ─────────────────────────┐
│ Name              Last Modified     │
│ ──────────────────────────────────  │
│ API_TOKEN         2025-06-22 10:30  │
│ DB_PASSWORD       2025-06-20 14:15  │
│ REGISTRY_KEY      2025-06-18 09:00  │
│                                     │
│ [A] Add  [E] Edit  [D] Delete       │
└─────────────────────────────────────┘
```

**Estimated effort:** Phase 1 is Low (regex replacement at config load). Phase 2 is Medium. Phase 3 is Medium.

**Priority:** P3 for full encrypted store. **But Phase 1 (env var expansion) should be P0** — it's trivial and immediately eliminates plaintext credentials.
