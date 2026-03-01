"""
Argus MCP - A central server for aggregating MCP server capabilities.

Argus MCP connects to multiple backend MCP servers (stdio/SSE) and exposes
their aggregated capabilities (tools, resources, prompts) through a unified
SSE endpoint.
"""

from argus_mcp.constants import SERVER_NAME, SERVER_VERSION

__version__ = SERVER_VERSION
__app_name__ = SERVER_NAME

__all__ = [
    "SERVER_NAME",
    "SERVER_VERSION",
    "__version__",
    "__app_name__",
]
