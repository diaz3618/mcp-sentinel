"""Authorization middleware for the MCP data plane.

Evaluates RBAC policies from the ``PolicyEngine`` against the
authenticated user's roles and the requested capability.

Slot order in the chain: **Auth → AUTHZ → Audit → Recovery → Routing**.

When authorization is disabled, all requests pass through.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_sentinel.bridge.middleware.chain import MCPHandler, RequestContext
from mcp_sentinel.server.auth.providers import UserIdentity
from mcp_sentinel.server.authz.engine import PolicyEngine
from mcp_sentinel.server.authz.policies import PolicyDecision

logger = logging.getLogger(__name__)


class AuthorizationError(Exception):
    """Raised when authorization fails (maps to HTTP 403)."""


class AuthzMiddleware:
    """MCP middleware that enforces RBAC policies.

    Parameters
    ----------
    engine:
        The :class:`PolicyEngine` to evaluate requests against.
    """

    def __init__(self, engine: PolicyEngine) -> None:
        self._engine = engine

    async def __call__(self, ctx: RequestContext, next_handler: MCPHandler) -> Any:
        """Evaluate authorization and continue or deny."""
        user: Optional[UserIdentity] = ctx.metadata.get("user")
        user_roles = list(user.roles) if user else []

        # Build resource identifier for policy matching
        resource = f"tool:{ctx.capability_name}"

        decision = self._engine.evaluate(user_roles, resource)

        if decision == PolicyDecision.DENY:
            subject = user.subject if user else "unknown"
            logger.warning(
                "Authorization DENIED: user=%s, resource=%s, roles=%s",
                subject,
                resource,
                user_roles,
            )
            raise AuthorizationError(
                f"Access denied for '{ctx.capability_name}' — "
                f"insufficient permissions (roles: {user_roles})"
            )

        return await next_handler(ctx)
