# Authentication

MCP Sentinel supports four incoming authentication modes. The mode is set in the
`incoming_auth` config section and applies to all MCP client connections.

## Auth Types

### `anonymous` (default)

No authentication. All clients are accepted with an anonymous identity.

```yaml
incoming_auth:
  type: anonymous
```

**Use case:** Development, trusted networks, testing.

### `local`

Static bearer token. Clients must send `Authorization: Bearer <token>` in their
connection. Token comparison uses constant-time `hmac.compare_digest` to prevent
timing attacks.

```yaml
incoming_auth:
  type: local
  token: "${SENTINEL_AUTH_TOKEN}"
```

**Use case:** Simple deployments, single-user setups.

### `jwt`

JWT validation via JWKS (JSON Web Key Set). Sentinel fetches the public keys
from a JWKS endpoint and validates token signatures, expiry, issuer, and
audience claims.

```yaml
incoming_auth:
  type: jwt
  jwks_uri: "https://auth.example.com/.well-known/jwks.json"
  issuer: "https://auth.example.com"
  audience: "mcp-sentinel"
  algorithms: ["RS256", "ES256"]
```

| Field | Required | Description |
|-------|----------|-------------|
| `jwks_uri` | Yes | URL to the JWKS endpoint |
| `issuer` | No | Expected `iss` claim |
| `audience` | No | Expected `aud` claim |
| `algorithms` | No | Allowed algorithms (default: `RS256`, `ES256`) |

**User identity extraction from JWT claims:**

| Claim | Maps To |
|-------|---------|
| `sub` | `UserIdentity.subject` |
| `email` | `UserIdentity.email` |
| `name` | `UserIdentity.name` |
| `roles` or `realm_access.roles` | `UserIdentity.roles` |

### `oidc`

OpenID Connect auto-discovery. Sentinel discovers the JWKS URI automatically
from the issuer's `/.well-known/openid-configuration` endpoint.

```yaml
incoming_auth:
  type: oidc
  issuer: "https://auth.example.com"
  audience: "mcp-sentinel"
```

This is equivalent to `jwt` mode but automatically constructs the JWKS URI from
the issuer URL.

## Identity Model

All auth providers produce a `UserIdentity`:

```python
@dataclass(frozen=True)
class UserIdentity:
    subject: str       # Unique user identifier
    email: str         # User email (optional)
    name: str          # Display name (optional)
    roles: list[str]   # Assigned roles (for RBAC)
    provider: str      # Auth provider name
    claims: dict       # Raw token claims

    @property
    def is_anonymous(self) -> bool: ...
```

The identity is injected into the middleware chain as `ctx.metadata["user"]` and
is available to audit logging and RBAC evaluation.

## Middleware Integration

The `AuthMiddleware` sits at the top of the middleware chain:

1. Extracts the bearer token from the request
2. Delegates to the configured `AuthProvider`
3. On success: injects `UserIdentity` into the request context
4. On failure: raises `AuthenticationError` (HTTP 401)

## Management API Auth

The management REST API (`/manage/v1/`) has its own separate auth via
`BearerAuthMiddleware`:

- Token configured via `server.management.token` or `SENTINEL_MGMT_TOKEN` env var
- If no token is configured, management API is open (no auth)
- `GET /manage/v1/health` is always public (no token required)

This is independent of the MCP client auth system.
