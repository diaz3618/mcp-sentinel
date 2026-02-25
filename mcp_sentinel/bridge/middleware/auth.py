"""Authentication middleware for the MCP data plane.

Validates incoming requests via the configured auth provider and
injects :class:`UserIdentity` into ``ctx.metadata["user"]``.

Slot order in the chain: **AUTH → Audit → Recovery → Routing**.

When auth is disabled (anonymous mode), a no-op identity is injected.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_sentinel.bridge.middleware.chain import MCPHandler, RequestContext
from mcp_sentinel.server.auth.providers import (
    AuthenticationError,
    AuthProviderRegistry,
)

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """MCP middleware that validates bearer tokens on incoming requests.

    Parameters
    ----------
    provider_registry:
        The :class:`AuthProviderRegistry` to delegate auth to.
    """

    def __init__(self, provider_registry: AuthProviderRegistry) -> None:
        self._registry = provider_registry

    async def __call__(self, ctx: RequestContext, next_handler: MCPHandler) -> Any:
        """Extract token from context, authenticate, and continue chain."""
        token: Optional[str] = ctx.metadata.get("auth_token")

        try:
            user = await self._registry.authenticate(token)
        except AuthenticationError as exc:
            logger.warning(
                "Auth failed for request %s (%s): %s",
                ctx.request_id,
                ctx.capability_name,
                exc,
            )
            raise

        # Inject user identity for downstream middleware (audit, authz)
        ctx.metadata["user"] = user
        if user.subject:
            ctx.metadata["user_subject"] = user.subject

        return await next_handler(ctx)
