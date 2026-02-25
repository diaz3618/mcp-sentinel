"""Starlette ASGI application factory and MCP server instance."""

import logging
from typing import Optional

from mcp.server import Server as McpServer
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp_sentinel.constants import (
    MANAGEMENT_API_PREFIX,
    POST_MESSAGES_PATH,
    SERVER_NAME,
    SSE_PATH,
    STREAMABLE_HTTP_PATH,
)
from mcp_sentinel.server.handlers import register_handlers
from mcp_sentinel.server.lifespan import app_lifespan
from mcp_sentinel.server.management import create_management_app
from mcp_sentinel.server.transport import handle_sse, handle_streamable_http, sse_transport

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
    mgmt_app = create_management_app()
    application = Starlette(
        lifespan=app_lifespan,
        routes=[
            Route(SSE_PATH, endpoint=handle_sse),
            Mount(POST_MESSAGES_PATH, app=sse_transport.handle_post_message),
            Route(
                STREAMABLE_HTTP_PATH,
                endpoint=handle_streamable_http,
                methods=["GET", "POST", "DELETE"],
            ),
            Mount(MANAGEMENT_API_PREFIX, app=mgmt_app),
        ],
    )
    # Store mgmt_app reference so lifespan can propagate service state to it.
    application.state.mgmt_app = mgmt_app  # type: ignore[attr-defined]
    logger.info(
        "Starlette ASGI app '%s' created. "
        "SSE GET on %s, POST on %s, Streamable HTTP on %s, Manage on %s",
        SERVER_NAME,
        SSE_PATH,
        POST_MESSAGES_PATH,
        STREAMABLE_HTTP_PATH,
        MANAGEMENT_API_PREFIX,
    )
    return application


# Default app instance for uvicorn import
app = create_app()
