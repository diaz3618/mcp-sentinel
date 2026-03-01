"""Bridge subpackage - manages backend connections and capability routing."""

from argus_mcp.bridge.capability_registry import CapabilityRegistry
from argus_mcp.bridge.client_manager import ClientManager
from argus_mcp.bridge.conflict import ConflictStrategy, create_strategy
from argus_mcp.bridge.filter import CapabilityFilter
from argus_mcp.bridge.groups import GroupManager
from argus_mcp.bridge.health import (
    CircuitBreaker,
    CircuitState,
    HealthChecker,
    HealthState,
)
from argus_mcp.bridge.rename import RenameMap

__all__ = [
    "CapabilityFilter",
    "CapabilityRegistry",
    "CircuitBreaker",
    "CircuitState",
    "ClientManager",
    "ConflictStrategy",
    "GroupManager",
    "HealthChecker",
    "HealthState",
    "RenameMap",
    "create_strategy",
]
