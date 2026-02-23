"""MCP handler functions - registered on the MCP server instance."""

import logging
from typing import Any, Dict, List, Optional

from mcp import types as mcp_types
from mcp.server import Server as McpServer

from mcp_sentinel.bridge.forwarder import forward_request
from mcp_sentinel.errors import BackendServerError

logger = logging.getLogger(__name__)


def register_handlers(mcp_server: McpServer) -> None:
    """Register all MCP protocol handlers on the server instance."""

    @mcp_server.list_tools()
    async def handle_list_tools() -> List[mcp_types.Tool]:
        logger.debug("Handling listTools request...")
        if not mcp_server.registry:
            raise BackendServerError("Registry is not initialized")
        tools = mcp_server.registry.get_aggregated_tools()
        logger.info("Returning %s aggregated tools", len(tools))
        return tools

    @mcp_server.list_resources()
    async def handle_list_resources() -> List[mcp_types.Resource]:
        logger.debug("Handling listResources request...")
        if not mcp_server.registry:
            raise BackendServerError("Registry is not initialized")
        resources = mcp_server.registry.get_aggregated_resources()
        logger.info("Returning %s aggregated resources", len(resources))
        return resources

    @mcp_server.list_prompts()
    async def handle_list_prompts() -> List[mcp_types.Prompt]:
        logger.debug("Handling listPrompts request...")
        if not mcp_server.registry:
            raise BackendServerError("Registry is not initialized")
        prompts = mcp_server.registry.get_aggregated_prompts()
        logger.info("Returning %s aggregated prompts", len(prompts))
        return prompts

    @mcp_server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> List[mcp_types.TextContent]:
        logger.debug("Handling callTool: name='%s'", name)
        result = await forward_request(
            name, "call_tool", arguments, mcp_server.registry, mcp_server.manager
        )
        if isinstance(result, mcp_types.CallToolResult):
            return result.content
        logger.error(
            "call_tool forwarding returned unexpected type: "
            "%s for tool '%s'", type(result), name,
        )
        raise BackendServerError(
            f"Backend returned invalid type for tool call '{name}'."
        )

    @mcp_server.read_resource()
    async def handle_read_resource(name: str) -> mcp_types.ReadResourceResult:
        logger.debug("Handling readResource: name='%s'", name)
        result = await forward_request(
            name, "read_resource", None, mcp_server.registry, mcp_server.manager
        )
        if isinstance(result, mcp_types.ReadResourceResult):
            return result
        logger.error(
            "read_resource forwarding returned unexpected type: "
            "%s for resource '%s'", type(result), name,
        )
        raise BackendServerError(
            f"Backend returned invalid type for resource read '{name}'."
        )

    @mcp_server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> mcp_types.GetPromptResult:
        logger.debug("Handling getPrompt: name='%s'", name)
        typed_args: Optional[Dict[str, str]] = None
        if arguments is not None:
            try:
                typed_args = {k: str(v) for k, v in arguments.items()}
            except Exception:
                logger.warning(
                    "Could not cast get_prompt arguments to Dict[str, str] "
                    "for prompt '%s'. Will fall back to original arguments.",
                    name,
                    exc_info=True,
                )

        result = await forward_request(
            name,
            "get_prompt",
            typed_args or arguments,
            mcp_server.registry,
            mcp_server.manager,
        )
        if isinstance(result, mcp_types.GetPromptResult):
            return result
        logger.error(
            "get_prompt forwarding returned unexpected type: "
            "%s for prompt '%s'", type(result), name,
        )
        raise BackendServerError(
            f"Backend returned invalid type for prompt '{name}'."
        )

    logger.debug("All MCP protocol handlers registered on server instance.")
