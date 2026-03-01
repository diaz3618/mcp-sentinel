"""Dashboard mode — server info, backends, events, and capabilities.

The main operational screen.  Kept intentionally clean: sidebar
(server selector, info, backends) + event log + capability tables.
All monitoring/operational panels live in dedicated mode screens
(Health, Security, Operations) accessible via keyboard shortcuts.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical

from argus_mcp.tui.screens.base import ArgusScreen
from argus_mcp.tui.widgets.backend_status import BackendStatusWidget
from argus_mcp.tui.widgets.capability_tables import CapabilitySection
from argus_mcp.tui.widgets.event_log import EventLogWidget
from argus_mcp.tui.widgets.server_info import ServerInfoWidget
from argus_mcp.tui.widgets.server_selector import ServerSelectorWidget


class DashboardScreen(ArgusScreen):
    """Main dashboard screen."""

    def on_show(self) -> None:
        """Trigger app-level initialization once the screen is shown."""
        if getattr(self, "_ds_init_done", False):
            return
        self._ds_init_done = True
        app = self.app
        if hasattr(app, "_init_after_mode_switch"):
            app._init_after_mode_switch()

    def compose_content(self) -> ComposeResult:
        with Horizontal(id="top-row"):
            with Vertical(id="sidebar"):
                yield ServerSelectorWidget(id="srv-selector")
                yield ServerInfoWidget()
                yield BackendStatusWidget()
            with Vertical(id="main-area"):
                yield EventLogWidget()
        yield CapabilitySection(id="cap-section")
