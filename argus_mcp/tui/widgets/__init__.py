"""TUI widget definitions."""

from argus_mcp.tui.widgets.backend_status import BackendStatusWidget
from argus_mcp.tui.widgets.capability_tables import CapabilitySection
from argus_mcp.tui.widgets.event_log import EventLogWidget
from argus_mcp.tui.widgets.server_info import ServerInfoWidget

__all__ = [
    "BackendStatusWidget",
    "CapabilitySection",
    "EventLogWidget",
    "ServerInfoWidget",
]
