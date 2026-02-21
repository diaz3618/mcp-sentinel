"""TUI widget definitions."""

from mcp_sentinel.tui.widgets.backend_status import BackendStatusWidget
from mcp_sentinel.tui.widgets.capability_tables import CapabilitySection
from mcp_sentinel.tui.widgets.event_log import EventLogWidget
from mcp_sentinel.tui.widgets.server_info import ServerInfoWidget

__all__ = [
    "BackendStatusWidget",
    "CapabilitySection",
    "EventLogWidget",
    "ServerInfoWidget",
]
