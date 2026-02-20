"""Bridge subpackage - manages backend connections and capability routing."""

from mcp_gateway.bridge.capability_registry import CapabilityRegistry
from mcp_gateway.bridge.client_manager import ClientManager

__all__ = [
    "ClientManager",
    "CapabilityRegistry",
]
