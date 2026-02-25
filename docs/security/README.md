# Security

MCP Sentinel provides layered security controls for both incoming client
connections and outgoing backend connections.

## Security Layers

```markdown
MCP Client
  │
  ▼
┌──────────────────────────┐
│  1. Incoming Auth        │  Verify client identity (JWT, OIDC, local token)
├──────────────────────────┤
│  2. RBAC Authorization   │  Check role-based policies
├──────────────────────────┤
│  3. Audit Logging        │  Record all operations (NIST SP 800-53)
├──────────────────────────┤
│  4. Secret Redaction     │  Scrub secrets from all log output
├──────────────────────────┤
│  5. Outgoing Auth        │  Authenticate to backends (OAuth2, static)
└──────────────────────────┘
  │
  ▼
Backend MCP Server
```

## Documentation

| Topic | Description |
|-------|-------------|
| [Authentication](authentication.md) | Incoming client auth (anonymous, local, JWT, OIDC) |
| [Authorization](authorization.md) | RBAC policy enforcement |
| [Secrets Management](secrets.md) | Encrypted secret store and resolution |
| [Outgoing Auth](outgoing-auth.md) | Backend authentication (static headers, OAuth2) |

## Security Defaults

| Feature | Default | Production Recommendation |
|---------|---------|--------------------------|
| Incoming auth | `anonymous` | `jwt` or `oidc` |
| Management API auth | disabled (no token) | Set `SENTINEL_MGMT_TOKEN` |
| RBAC | disabled | Enable with `default_effect: deny` |
| Audit logging | enabled | Keep enabled |
| Secret provider | `file` (Fernet) | `file` or `keyring` |
| Log redaction | automatic | Automatic when secrets are resolved |
