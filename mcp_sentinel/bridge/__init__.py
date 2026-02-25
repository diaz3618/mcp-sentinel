"""Bridge subpackage - manages backend connections and capability routing."""

from mcp_sentinel.bridge.capability_registry import CapabilityRegistry
from mcp_sentinel.bridge.client_manager import ClientManager
from mcp_sentinel.bridge.conflict import ConflictStrategy, create_strategy
from mcp_sentinel.bridge.filter import CapabilityFilter
from mcp_sentinel.bridge.groups import GroupManager
from mcp_sentinel.bridge.health import (
    CircuitBreaker,
    CircuitState,
    HealthChecker,
    HealthState,
)
from mcp_sentinel.bridge.rename import RenameMap

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
