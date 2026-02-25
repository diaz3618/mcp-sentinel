"""Optimizer — find_tool / call_tool meta-tools for managing tool explosion.

When enabled, replaces the full tool catalog with two meta-tools:
- ``find_tool`` — semantic search across all registered tools
- ``call_tool`` — dynamic invocation by exact tool name
"""

from mcp_sentinel.bridge.optimizer.meta_tools import META_TOOLS, build_meta_tools
from mcp_sentinel.bridge.optimizer.search import ToolIndex

__all__ = [
    "META_TOOLS",
    "ToolIndex",
    "build_meta_tools",
]
