"""MCP request forwarding logic for routing calls to backend servers."""

import asyncio
import logging
from typing import Any, Dict, Optional

from mcp import types as mcp_types

from mcp_gateway.errors import BackendServerError

logger = logging.getLogger(__name__)


async def forward_request(
    cap_name_full: str,
    mcp_method: str,
    args: Optional[Dict[str, Any]],
    registry: Any,
    manager: Any,
) -> Any:
    """
    Forward an MCP request to the correct backend server.

    Args:
        cap_name_full: The exposed capability name to forward.
        mcp_method: The MCP method name (call_tool, read_resource, get_prompt).
        args: Optional arguments to pass to the backend method.
        registry: The CapabilityRegistry instance for routing.
        manager: The ClientManager instance for session access.

    Returns:
        The result from the backend server.

    Raises:
        BackendServerError: If core components are missing or backend errors occur.
        ValueError: If the capability cannot be resolved.
        RuntimeError: If the backend session is unavailable.
        NotImplementedError: If the MCP method is unknown.
    """
    logger.info(
        f"Forwarding request: capability='{cap_name_full}', "
        f"method='{mcp_method}', args={args}"
    )

    if not registry or not manager:
        logger.error(
            "registry or manager is unset during forwarding. "
            "This is a critical internal error."
        )
        raise BackendServerError(
            "Internal gateway error: core components not initialized."
        )

    route_info = registry.resolve_capability(cap_name_full)
    if not route_info:
        logger.warning(
            f"Unable to resolve capability name '{cap_name_full}'. "
            "MCP client should receive an error."
        )
        raise ValueError(f"Capability '{cap_name_full}' does not exist.")

    svr_name, orig_cap_name = route_info
    logger.debug(
        f"Capability '{cap_name_full}' resolved to server '{svr_name}' "
        f"capability '{orig_cap_name}'."
    )

    session = manager.get_session(svr_name)
    if not session:
        logger.error(
            f"Unable to get active session for server '{svr_name}' "
            f"while forwarding '{cap_name_full}'."
        )
        raise RuntimeError(
            f"Unable to connect to backend server '{svr_name}' "
            f"providing '{cap_name_full}' (session missing or lost)."
        )

    try:
        target_method_on_session = getattr(session, mcp_method)
    except AttributeError:
        logger.exception(
            f"Internal programming error: method '{mcp_method}' "
            "not found on ClientSession."
        )
        raise NotImplementedError(
            f"Internal gateway error: forward method '{mcp_method}' not found."
        )

    try:
        logger.debug(
            f"Calling backend '{svr_name}' method '{mcp_method}' "
            f"(original capability: '{orig_cap_name}')"
        )
        result: Any
        if mcp_method == "call_tool":
            result = await target_method_on_session(
                name=orig_cap_name, arguments=args or {}
            )
        elif mcp_method == "read_resource":
            content, mime_type = await target_method_on_session(
                name=orig_cap_name
            )
            result = mcp_types.ReadResourceResult(
                content=content, mime_type=mime_type
            )
        elif mcp_method == "get_prompt":
            result = await target_method_on_session(
                name=orig_cap_name, arguments=args
            )
        else:
            logger.error(
                f"Internal programming error: unknown forwarding method "
                f"'{mcp_method}'."
            )
            raise NotImplementedError(
                f"Internal gateway error: cannot handle request type "
                f"'{mcp_method}'."
            )

        logger.info(
            f"Received backend result from '{svr_name}' for '{mcp_method}' "
            f"(capability: '{cap_name_full}')."
        )
        return result

    except asyncio.TimeoutError:
        logger.error(
            f"Timeout communicating with backend '{svr_name}' "
            f"(capability: '{cap_name_full}', method: '{mcp_method}')."
        )
        raise
    except (ConnectionError, BrokenPipeError) as conn_e:
        logger.error(
            f"Connection lost to backend '{svr_name}' "
            f"(capability: '{cap_name_full}', method: '{mcp_method}'): "
            f"{type(conn_e).__name__}"
        )
        raise
    except BackendServerError:
        logger.warning(
            f"Backend '{svr_name}' reported a server error "
            f"while handling '{cap_name_full}'."
        )
        raise
    except Exception as e_fwd:
        logger.exception(
            f"Unexpected error forwarding request to backend '{svr_name}' "
            f"(capability: '{cap_name_full}', method: '{mcp_method}')"
        )
        raise BackendServerError(
            f"Unexpected backend error while handling request "
            f"'{cap_name_full}' from '{svr_name}': {type(e_fwd).__name__}"
        ) from e_fwd
