"""Runtime service layer for Argus MCP.

Re-exports the key symbols so callers can write::

    from argus_mcp.runtime import ArgusService, ServiceState, ServiceStatus
"""

from argus_mcp.runtime.models import (
    BackendInfo,
    CapabilityInfo,
    ServiceState,
    ServiceStatus,
)
from argus_mcp.runtime.service import ArgusService

__all__ = [
    "BackendInfo",
    "CapabilityInfo",
    "ArgusService",
    "ServiceState",
    "ServiceStatus",
]
