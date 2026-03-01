"""Custom Textual messages for MCP Sentinel TUI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.message import Message


class CapabilitiesReady(Message):
    """Posted once capabilities have been discovered and are available."""

    def __init__(
        self,
        tools: List[Any],
        resources: List[Any],
        prompts: List[Any],
        route_map: Optional[Dict[str, tuple]] = None,
    ) -> None:
        self.tools = tools
        self.resources = resources
        self.prompts = prompts
        self.route_map = route_map or {}
        super().__init__()


class ConnectionLost(Message):
    """Posted when the TUI loses its HTTP connection to the server."""

    def __init__(self, reason: str = "Connection lost") -> None:
        self.reason = reason
        super().__init__()


class ConnectionRestored(Message):
    """Posted when the TUI re-establishes its HTTP connection."""

    def __init__(self) -> None:
        super().__init__()


class ConfigSyncUpdate(Message):
    """Posted when the server reports a config file change.

    Carries the details needed by :class:`SyncStatusWidget` to refresh.
    """

    def __init__(
        self,
        config_file: str = "",
        config_hash: str = "",
        sync_type: str = "changed",
        details: str = "",
        timestamp: str = "",
    ) -> None:
        self.config_file = config_file
        self.config_hash = config_hash
        self.sync_type = sync_type
        self.details = details
        self.timestamp = timestamp
        super().__init__()
