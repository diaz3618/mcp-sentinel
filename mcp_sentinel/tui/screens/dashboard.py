"""Dashboard mode — shows server info, backends, events, and capabilities.

The main operational screen that displays the full Sentinel dashboard
layout with sidebar, event log, and capability tables.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical

from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.widgets.backend_status import BackendStatusWidget
from mcp_sentinel.tui.widgets.capability_tables import CapabilitySection
from mcp_sentinel.tui.widgets.event_log import EventLogWidget
from mcp_sentinel.tui.widgets.server_info import ServerInfoWidget
from mcp_sentinel.tui.widgets.server_selector import ServerSelectorWidget


class DashboardScreen(SentinelScreen):
    """Main dashboard screen."""

    _initialized: bool = False

    def on_show(self) -> None:
        """Trigger app-level initialization once the screen is shown.

        In Textual 7.x, ``call_after_refresh`` on the *App* fires before
        the mode-screen's widgets are composed, so we call back into the
        app from the screen's ``on_show`` instead.  The guard flag
        prevents re-initialization on subsequent mode switches.
        """
        if self._initialized:
            return
        self._initialized = True
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
