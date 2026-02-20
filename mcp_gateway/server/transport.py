"""SSE transport handling for MCP connections."""

import logging

from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from starlette.requests import Request

from mcp_gateway.constants import POST_MESSAGES_PATH, SERVER_NAME, SERVER_VERSION

logger = logging.getLogger(__name__)

# Module-level SSE transport instance
sse_transport = SseServerTransport(POST_MESSAGES_PATH)


async def handle_sse(request: Request) -> None:
    """Handle incoming SSE connection requests."""
    from mcp_gateway.server.app import mcp_server

    logger.debug(f"Received new SSE connection request (GET): {request.url}")

    if not mcp_server.manager or not mcp_server.registry:
        logger.error(
            "manager or registry is unset in handle_sse. "
            "Missing critical components; cannot handle SSE connection."
        )
        return

    async with sse_transport.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (read_stream, write_stream):
        try:
            srv_caps = {}
            if mcp_server.registry:
                srv_caps = mcp_server.get_capabilities(
                    NotificationOptions(), {}
                )
            else:
                logger.warning(
                    "mcp_server.registry is unset; SSE initialization "
                    "will use empty capabilities."
                )
            logger.debug(
                f"Server capabilities for SSE connection: {srv_caps}"
            )
        except Exception as e_caps:
            logger.exception(
                f"Error getting mcp_server.get_capabilities "
                f"for SSE connection: {e_caps}"
            )
            srv_caps = {}

        init_opts = InitializationOptions(
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            capabilities=srv_caps,
        )
        logger.debug(
            f"Running mcp_server.run (MCP main loop) for SSE connection "
            f"with options: {init_opts}"
        )
        await mcp_server.run(read_stream, write_stream, init_opts)
    logger.debug(f"SSE connection closed: {request.url}")
