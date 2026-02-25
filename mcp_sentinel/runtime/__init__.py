"""Runtime service layer for MCP Sentinel.

Re-exports the key symbols so callers can write::

    from mcp_sentinel.runtime import SentinelService, ServiceState, ServiceStatus
"""

from mcp_sentinel.runtime.models import (
    BackendInfo,
    CapabilityInfo,
    ServiceState,
    ServiceStatus,
)
from mcp_sentinel.runtime.service import SentinelService

__all__ = [
    "BackendInfo",
    "CapabilityInfo",
    "SentinelService",
    "ServiceState",
    "ServiceStatus",
]
