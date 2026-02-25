"""MCP Server Registry — client, models, and cache.

Provides a read-only client for the MCP Registry API v0.1
(as implemented by toolhive-registry-server) and a local
JSON file cache for offline/fallback usage.
"""

from mcp_sentinel.registry.client import RegistryClient
from mcp_sentinel.registry.models import ServerEntry, ServerPage

__all__ = [
    "RegistryClient",
    "ServerEntry",
    "ServerPage",
]
