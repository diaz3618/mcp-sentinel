"""Management API package.

Exposes ``create_management_app`` to build the management ASGI sub-app with auth.
"""

from starlette.applications import Starlette
from starlette.middleware import Middleware

from mcp_sentinel.server.management.auth import BearerAuthMiddleware, resolve_token
from mcp_sentinel.server.management.router import management_routes


def create_management_app() -> Starlette:
    """Build the management sub-application with auth middleware.

    Returns a Starlette app wrapping the management routes with
    ``BearerAuthMiddleware``.  The token is resolved from env var
    or config at construction time.
    """
    token = resolve_token()
    mgmt_app = Starlette(
        routes=management_routes.routes,
        middleware=[Middleware(BearerAuthMiddleware, token=token)],
    )
    return mgmt_app


__all__ = ["create_management_app", "management_routes"]
