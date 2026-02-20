"""MCP request forwarding logic for routing calls to backend servers."""

import asyncio
import logging
from typing import Any, Dict, Optional

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
        "Forwarding request: capability='%s', method='%s', args=%s",
        cap_name_full,
        mcp_method,
        args,
    )

    if not registry or not manager:
        logger.error(
            "registry or manager is unset during forwarding. " "This is a critical internal error."
        )
        raise BackendServerError("Internal gateway error: core components not initialized.")

    route_info = registry.resolve_capability(cap_name_full)
    if not route_info:
        logger.warning(
            "Unable to resolve capability name '%s'. " "MCP client should receive an error.",
            cap_name_full,
        )
        raise ValueError(f"Capability '{cap_name_full}' does not exist.")

    svr_name, orig_cap_name = route_info
    logger.debug(
        "Capability '%s' resolved to server '%s' capability '%s'.",
        cap_name_full,
        svr_name,
        orig_cap_name,
    )

    session = manager.get_session(svr_name)
    if not session:
        logger.error(
            "Unable to get active session for server '%s' " "while forwarding '%s'.",
            svr_name,
            cap_name_full,
        )
        raise RuntimeError(
            f"Unable to connect to backend server '{svr_name}' "
            f"providing '{cap_name_full}' (session missing or lost)."
        )

    _ALLOWED_MCP_METHODS = {"call_tool", "read_resource", "get_prompt"}
    if mcp_method not in _ALLOWED_MCP_METHODS:
        logger.error(
            "Rejecting unknown MCP method '%s' (allowed: %s)",
            mcp_method,
            _ALLOWED_MCP_METHODS,
        )
        raise NotImplementedError(f"Internal gateway error: unsupported method '{mcp_method}'.")

    try:
        target_method_on_session = getattr(session, mcp_method)
    except AttributeError:
        logger.exception(
            "Internal programming error: method '%s' " "not found on ClientSession.",
            mcp_method,
        )
        raise NotImplementedError(
            f"Internal gateway error: forward method '{mcp_method}' not found."
        )

    try:
        logger.debug(
            "Calling backend '%s' method '%s' " "(original capability: '%s')",
            svr_name,
            mcp_method,
            orig_cap_name,
        )
        result: Any
        if mcp_method == "call_tool":
            result = await target_method_on_session(name=orig_cap_name, arguments=args or {})
        elif mcp_method == "read_resource":
            read_result = await target_method_on_session(uri=orig_cap_name)
            result = read_result
        elif mcp_method == "get_prompt":
            result = await target_method_on_session(name=orig_cap_name, arguments=args)
        else:
            logger.error(
                "Internal programming error: unknown forwarding method " "'%s'.",
                mcp_method,
            )
            raise NotImplementedError(
                f"Internal gateway error: cannot handle request type " f"'{mcp_method}'."
            )

        logger.info(
            "Received backend result from '%s' for '%s' " "(capability: '%s').",
            svr_name,
            mcp_method,
            cap_name_full,
        )
        return result

    except asyncio.TimeoutError:
        logger.error(
            "Timeout communicating with backend '%s' " "(capability: '%s', method: '%s').",
            svr_name,
            cap_name_full,
            mcp_method,
        )
        raise
    except (ConnectionError, BrokenPipeError) as conn_e:
        logger.error(
            "Connection lost to backend '%s' " "(capability: '%s', method: '%s'): %s",
            svr_name,
            cap_name_full,
            mcp_method,
            type(conn_e).__name__,
        )
        raise
    except BackendServerError:
        logger.warning(
            "Backend '%s' reported a server error " "while handling '%s'.",
            svr_name,
            cap_name_full,
        )
        raise
    except Exception as e_fwd:
        logger.exception(
            "Unexpected error forwarding request to backend '%s' "
            "(capability: '%s', method: '%s')",
            svr_name,
            cap_name_full,
            mcp_method,
        )
        raise BackendServerError(
            f"Unexpected backend error while handling request "
            f"'{cap_name_full}' from '{svr_name}': {type(e_fwd).__name__}"
        ) from e_fwd
