"""Server subpackage - Starlette ASGI app, lifespan, handlers, transport."""

from argus_mcp.server.app import create_app

__all__ = [
    "create_app",
]
