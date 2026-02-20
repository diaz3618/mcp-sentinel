"""Starlette ASGI application factory and MCP server instance."""

import logging
from typing import Optional

from mcp.server import Server as McpServer
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp_gateway.constants import POST_MESSAGES_PATH, SERVER_NAME, SSE_PATH
from mcp_gateway.server.handlers import register_handlers
from mcp_gateway.server.lifespan import app_lifespan
from mcp_gateway.server.transport import handle_sse, sse_transport

logger = logging.getLogger(__name__)

# Module-level MCP server instance
mcp_server = McpServer(SERVER_NAME)
mcp_server.manager: Optional[object] = None  # type: ignore[assignment]
mcp_server.registry: Optional[object] = None  # type: ignore[assignment]
logger.debug("Underlying MCP server instance '%s' created.", mcp_server.name)

# Register all MCP handlers
register_handlers(mcp_server)


def create_app() -> Starlette:
    """Create and return the Starlette ASGI application."""
    application = Starlette(
        lifespan=app_lifespan,
        routes=[
            Route(SSE_PATH, endpoint=handle_sse),
            Mount(POST_MESSAGES_PATH, app=sse_transport.handle_post_message),
        ],
    )
    logger.info(
        "Starlette ASGI app '%s' created. SSE GET on %s, POST on %s",
        SERVER_NAME,
        SSE_PATH,
        POST_MESSAGES_PATH,
    )
    return application


# Default app instance for uvicorn import
app = create_app()
