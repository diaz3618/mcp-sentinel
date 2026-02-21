# Outgoing Authentication (Backend Credentials)

> **Status in analysis table:** "Explain" — This is a security gap that needs explanation.

---

## What It Is

Outgoing authentication handles **injecting credentials when MCP Sentinel connects to backend MCP servers**. Many MCP servers require authentication (API keys, OAuth tokens, service accounts), but today MCP Sentinel has no mechanism to supply these credentials.

This is different from incoming auth (validating clients). This is about MCP Sentinel acting as an **authenticated client** when calling backends.

## How ToolHive Implements It

ToolHive's `pkg/vmcp/auth/outgoing/` package implements a per-backend credential strategy:

### Strategy Types

1. **Static Headers** — Fixed key-value headers injected into every request
   ```yaml
   backends:
     github-server:
       auth:
         type: static
         headers:
           Authorization: "Bearer ghp_xxxxxxxxxxxx"
   ```

2. **Token Exchange (RFC 8693)** — Exchange the incoming user's token for a backend-specific token
   - The gateway presents the user's JWT to a token exchange endpoint
   - Receives a scoped token for the specific backend
   - Enables per-user permissions at the backend level

3. **OAuth2 Client Credentials** — Machine-to-machine authentication
   - The gateway authenticates as itself (not as a user)
   - Uses client_id + client_secret for a token
   - Suitable for shared service accounts

### Token Caching
All strategies feed through a token cache:
- In-memory cache with TTL based on token expiry
- Prevents re-authentication on every request
- Thread-safe with atomic operations

### Transport Integration
Credentials are injected at the transport layer via a chain pattern:
```
OutgoingAuth → TransportClient → Backend
```
The transport client wraps the underlying HTTP/SSE connection, intercepting outbound requests to add headers.

## How This Improves MCP Sentinel

### Without Outgoing Auth
- Backend credentials must be hardcoded or passed via environment variables to subprocess stdio servers
- SSE backends that require auth headers cannot be connected at all
- No way to rotate credentials without restarting
- No per-user credential delegation

### With Outgoing Auth
- SSE/streamable-http backends with auth requirements become accessible
- Credentials are managed centrally in config
- Environment variable expansion (`$API_TOKEN`) keeps secrets out of plaintext
- Future: token exchange enables per-user access control at the backend level

## Implementation Path for MCP Sentinel

### Phase 1: Static Headers (P2)
The simplest and most impactful version — just inject headers from config:

```json
{
  "mcpServers": {
    "protected-server": {
      "transport": "sse",
      "url": "https://api.example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer $API_TOKEN",
        "X-Custom-Header": "value"
      }
    }
  }
}
```

In `client_manager.py`, pass these headers when creating the SSE/HTTP client:

```python
async def _init_sse_backend(self, name: str, cfg: dict):
    headers = self._expand_env_vars(cfg.get("headers", {}))
    async with sse_client(cfg["url"], headers=headers) as streams:
        ...
```

### Phase 2: OAuth2 Client Credentials (P3)
```python
class OAuth2ClientCredentials:
    def __init__(self, token_url: str, client_id: str, client_secret: str):
        self._cache: str | None = None
        self._expires_at: float = 0
    
    async def get_token(self) -> str:
        if time.time() < self._expires_at:
            return self._cache
        # Fetch new token via httpx POST
        ...
```

### Phase 3: Token Exchange (P3+)
Only needed for multi-user deployments where backend access must be user-scoped.

**Estimated effort:** Phase 1 is Low (just pass headers through). Phases 2-3 are Medium-High.
