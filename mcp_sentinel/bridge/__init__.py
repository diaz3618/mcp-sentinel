"""Bridge subpackage - manages backend connections and capability routing."""

from mcp_sentinel.bridge.capability_registry import CapabilityRegistry
from mcp_sentinel.bridge.client_manager import ClientManager

__all__ = [
    "ClientManager",
    "CapabilityRegistry",
]
