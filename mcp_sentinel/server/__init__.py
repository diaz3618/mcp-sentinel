"""Server subpackage - Starlette ASGI app, lifespan, handlers, transport."""

from mcp_sentinel.server.app import create_app

__all__ = [
    "create_app",
]
