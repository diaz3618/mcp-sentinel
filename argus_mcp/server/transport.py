"""SSE and streamable HTTP transport handling for MCP connections."""

import logging
import uuid

from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.requests import Request
from starlette.responses import Response

from argus_mcp.constants import POST_MESSAGES_PATH, SERVER_NAME, SERVER_VERSION

logger = logging.getLogger(__name__)

# Module-level SSE transport instance
sse_transport = SseServerTransport(POST_MESSAGES_PATH)


async def handle_sse(request: Request) -> None:
    """Handle incoming SSE connection requests."""
    from argus_mcp.server.app import mcp_server

    logger.debug("Received new SSE connection request (GET): %s", request.url)

    if not mcp_server.manager or not mcp_server.registry:
        logger.error(
            "manager or registry is unset in handle_sse. "
            "Missing critical components; cannot handle SSE connection."
        )
        return

    # ── Session management ───────────────────────────────────────────
    session_mgr = getattr(mcp_server, "session_manager", None)
    session = None
    if session_mgr is not None:
        route_map = mcp_server.registry.get_route_map()
        # route_map: tool_name → (backend_name, orig_name); flatten to tool_name → backend_name
        routing_table = {k: v[0] for k, v in route_map.items()} if route_map else {}
        session = session_mgr.create_session(
            routing_table=routing_table,
            capability_snapshot={
                "tools": len(mcp_server.registry.get_aggregated_tools()),
                "resources": len(mcp_server.registry.get_aggregated_resources()),
                "prompts": len(mcp_server.registry.get_aggregated_prompts()),
            },
            transport_type="sse",
        )

    async with sse_transport.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (read_stream, write_stream):
        try:
            srv_caps = {}
            if mcp_server.registry:
                srv_caps = mcp_server.get_capabilities(NotificationOptions(), {})
            else:
                logger.warning(
                    "mcp_server.registry is unset; SSE initialization "
                    "will use empty capabilities."
                )
            logger.debug("Server capabilities for SSE connection: %s", srv_caps)
        except Exception as e_caps:
            logger.exception(
                "Error getting mcp_server.get_capabilities " "for SSE connection: %s",
                e_caps,
            )
            srv_caps = {}

        init_opts = InitializationOptions(
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            capabilities=srv_caps,
        )
        logger.debug(
            "Running mcp_server.run (MCP main loop) for SSE connection " "with options: %s",
            init_opts,
        )
        await mcp_server.run(read_stream, write_stream, init_opts)
    # ── Clean up session on disconnect ───────────────────────────────
    if session is not None and session_mgr is not None:
        session_mgr.remove_session(session.id)
    logger.debug("SSE connection closed: %s", request.url)


async def handle_streamable_http(request: Request) -> Response:
    """Handle incoming streamable HTTP requests (POST/GET/DELETE on /mcp)."""
    from argus_mcp.server.app import mcp_server

    logger.debug("Received streamable HTTP request (%s): %s", request.method, request.url)

    if not mcp_server.manager or not mcp_server.registry:
        logger.error(
            "manager or registry is unset in handle_streamable_http. "
            "Missing critical components; cannot handle request."
        )
        return Response(status_code=503, content="Service not ready")

    # Each request creates a per-session transport.
    session_id = request.headers.get("mcp-session-id") or str(uuid.uuid4())
    transport = StreamableHTTPServerTransport(mcp_session_id=session_id)

    # ── Session management ───────────────────────────────────────────
    session_mgr = getattr(mcp_server, "session_manager", None)
    if session_mgr is not None:
        existing = session_mgr.get_session(session_id)
        if existing is None:
            route_map = mcp_server.registry.get_route_map()
            routing_table = {k: v[0] for k, v in route_map.items()} if route_map else {}
            session_mgr.create_session(
                routing_table=routing_table,
                capability_snapshot={
                    "tools": len(mcp_server.registry.get_aggregated_tools()),
                    "resources": len(mcp_server.registry.get_aggregated_resources()),
                    "prompts": len(mcp_server.registry.get_aggregated_prompts()),
                },
                transport_type="streamable_http",
                session_id=session_id,
            )

    async with transport.connect() as (read_stream, write_stream):
        try:
            srv_caps = {}
            if mcp_server.registry:
                srv_caps = mcp_server.get_capabilities(NotificationOptions(), {})
            else:
                logger.warning(
                    "mcp_server.registry is unset; streamable HTTP " "will use empty capabilities."
                )
        except Exception as e_caps:
            logger.exception(
                "Error getting capabilities for streamable HTTP: %s",
                e_caps,
            )
            srv_caps = {}

        init_opts = InitializationOptions(
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            capabilities=srv_caps,
        )

        # Run the transport handler in background while we run the MCP server.
        import asyncio

        server_task = asyncio.create_task(mcp_server.run(read_stream, write_stream, init_opts))
        try:
            await transport.handle_request(request.scope, request.receive, request._send)
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    logger.debug("Streamable HTTP request completed: %s", request.url)
