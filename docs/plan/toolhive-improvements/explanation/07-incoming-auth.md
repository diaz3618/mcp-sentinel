# Incoming Authentication

> **Status in analysis table:** "Explain" — This is a security gap that needs explanation.

---

## What It Is

Incoming authentication validates the identity of **clients connecting to MCP Sentinel**. Today, anyone who can reach the SSE endpoint can use the gateway. There is no way to:

- Verify who is connecting
- Restrict access to authorized users
- Audit which user made which tool call

## How ToolHive Implements It

ToolHive's `pkg/auth/` package provides three authentication modes, selected per-deployment:

### 1. OIDC / OAuth2 (`oidc_authenticator.go`)
- Validates JWT access tokens from any OIDC provider (Okta, Auth0, Azure AD, Keycloak)
- Uses OIDC discovery (`/.well-known/openid-configuration`) to fetch public signing keys
- Validates `iss`, `aud`, `exp`, `nbf` claims
- Extracts user identity + roles for downstream authorization

### 2. Local JWT (`local_authenticator.go`)
- Self-signed JWTs using a shared secret or RSA key pair
- No external identity provider required
- Suitable for internal/dev deployments

### 3. Anonymous (`anonymous_authenticator.go`)
- No authentication — all requests are treated as anonymous
- Used for local development or fully trusted networks
- Explicit opt-in (you must configure `auth: anonymous`)

The authentication middleware sits at position 3 in the 8-layer middleware chain, after recovery and header validation. It runs before audit, authorization, and MCP parsing.

## How This Improves MCP Sentinel

### Without Authentication
- Any network-reachable client can use the gateway
- No user identity for audit trails
- No foundation for authorization (you can't restrict tools by user if you don't know who the user is)
- Unsuitable for any shared or production deployment

### With Authentication
- Only authorized clients can connect
- Every request carries a verified user identity
- Audit logs can attribute actions to specific users
- Foundation for per-user authorization (e.g., "user A can call tool X but not tool Y")

## Implementation Path for MCP Sentinel

Since MCP Sentinel uses Starlette as its ASGI server, authentication is a natural fit as Starlette middleware:

```python
class JWTAuthMiddleware:
    """Validate Bearer tokens on SSE/HTTP connections."""
    
    def __init__(self, app, *, jwks_url: str | None = None, secret: str | None = None):
        self.app = app
        # Configure validator based on OIDC discovery or local secret
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            token = self._extract_bearer(headers)
            if token:
                user = await self._validate(token)
                scope["user"] = user  # Available downstream
            elif self.required:
                return await self._send_401(send)
        await self.app(scope, receive, send)
```

### Config Example

```json
{
  "auth": {
    "mode": "oidc",
    "issuer": "https://auth.example.com",
    "audience": "mcp-sentinel",
    "required": true
  }
}
```

Or for simple deployments:

```json
{
  "auth": {
    "mode": "local",
    "secret": "$JWT_SECRET"
  }
}
```

### Dependencies
- `PyJWT` or `python-jose` for JWT validation
- `httpx` for OIDC discovery (already a dependency)

**Estimated effort:** High — JWT validation itself is straightforward, but it requires careful testing of token flows, key rotation, and error handling. OIDC discovery adds network error handling complexity.

**Priority:** P3 — only needed for shared/production deployments, not single-user local usage.
