# Authorization (Policy-Based Access Control)

> **Status in analysis table:** "Explain" — This feature depends on incoming auth being implemented first.

---

## What It Is

Authorization decides **what an authenticated user is allowed to do**. Authentication answers "who are you?" — authorization answers "are you allowed to call this tool?"

This is critical for shared deployments where different users should have different access levels:
- Admins can call any tool
- Developers can call code-related tools but not deployment tools
- Read-only users can call query tools but not mutation tools

## How ToolHive Implements It

ToolHive supports two authorization backends:

### 1. Cedar Policies (`pkg/authz/cedar/`)

[Cedar](https://www.cedarpolicy.com/) is Amazon's policy language. ToolHive maps MCP operations to Cedar authorization requests:

```
MCP Method → (Feature, Operation) → Cedar Request
```

Mapping examples:
| MCP Method | Feature | Operation |
|------------|---------|-----------|
| `tools/list` | `tools` | `list` |
| `tools/call` | `tools` | `execute` |
| `resources/read` | `resources` | `read` |
| `prompts/get` | `prompts` | `read` |

Cedar policy example:
```cedar
// Allow developers to list and call tools, but only read resources
permit(
  principal in Group::"developers",
  action in [Action::"tools.list", Action::"tools.execute", Action::"resources.read"],
  resource
);

// Deny all users from calling destructive tools
forbid(
  principal,
  action == Action::"tools.execute",
  resource in ToolSet::"destructive"
);
```

### 2. HTTP PDP (`pkg/authz/http_pdp/`)

External Policy Decision Point — ToolHive sends an authorization request to an HTTP endpoint:

```json
POST /authorize
{
  "subject": { "id": "user@example.com", "roles": ["developer"] },
  "action": { "method": "tools/call", "tool": "deploy_production" },
  "resource": { "backend": "deploy-server" }
}
```

Response: `{ "allowed": true }` or `{ "allowed": false, "reason": "..." }`

This lets you plug in external policy engines like OPA (Open Policy Agent), Cerbos, or Permit.io.

## How This Improves MCP Sentinel

### Without Authorization
- All authenticated users have identical access
- No way to restrict tools by user role
- Destructive tools (delete, deploy, drop) are equally available to everyone
- Cannot satisfy compliance requirements for segregation of duties

### With Authorization
- Fine-grained per-user, per-tool access control
- Role-based access (admin/developer/viewer patterns)
- Audit trail of authorization decisions (who was allowed/denied what)
- Compliance with organizational security policies

## Implementation Path for MCP Sentinel

### Recommended Approach: Simple Role-Based Policies

Cedar has limited Python ecosystem support, and HTTP PDP adds deployment complexity. For MCP Sentinel, a simpler approach:

```json
{
  "authorization": {
    "enabled": true,
    "policies": [
      {
        "role": "admin",
        "allow": "*"
      },
      {
        "role": "developer",
        "allow": ["tools/list", "tools/call", "resources/read"],
        "deny_tools": ["deploy_production", "drop_database"]
      },
      {
        "role": "viewer",
        "allow": ["tools/list", "resources/list", "resources/read", "prompts/list"]
      }
    ],
    "default": "deny"
  }
}
```

Implementation as middleware:

```python
class AuthorizationMiddleware:
    async def __call__(self, request: MCPRequest, next):
        user = request.context.get("user")  # From auth middleware
        if not user:
            return MCPError("unauthorized")
        
        if not self.policy.allows(user.role, request.method, request.tool_name):
            return MCPError("forbidden", f"Role '{user.role}' cannot {request.method}")
        
        return await next(request)
```

### Prerequisites
- **Incoming authentication must be implemented first** — you can't authorize users you can't identify
- User identity must include role information (via JWT claims or a role mapping config)

### Future: External PDP
For advanced deployments, support calling an external authorization service:

```json
{
  "authorization": {
    "mode": "http_pdp",
    "url": "https://authz.internal/v1/authorize",
    "timeout_ms": 100,
    "cache_ttl_seconds": 60
  }
}
```

**Estimated effort:** Medium (simple role-based). High (external PDP). Depends on incoming auth (P3).

**Priority:** P3 — only relevant for multi-user/shared deployments.
