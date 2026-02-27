"""Health mode — backend health, sessions, and version drift.

Aggregates monitoring widgets into a tabbed layout so the
Dashboard stays clean.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import TabbedContent, TabPane

from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.widgets.health_panel import HealthPanel
from mcp_sentinel.tui.widgets.server_groups import ServerGroupsWidget
from mcp_sentinel.tui.widgets.sessions_panel import SessionsPanel
from mcp_sentinel.tui.widgets.version_drift import VersionDriftPanel


class HealthScreen(SentinelScreen):
    """Health monitoring mode — per-backend status, sessions, versions."""

    def compose_content(self) -> ComposeResult:
        with TabbedContent(id="health-tabs"):
            with TabPane("Status", id="tab-health-status"):
                yield HealthPanel(id="health-panel-widget")
            with TabPane("Sessions", id="tab-health-sessions"):
                yield SessionsPanel(id="sessions-panel-widget")
            with TabPane("Versions", id="tab-health-versions"):
                yield VersionDriftPanel(id="version-drift-widget")
            with TabPane("Server Groups", id="tab-health-groups"):
                yield ServerGroupsWidget(id="server-groups-widget")

    def on_show(self) -> None:
        """Refresh health data from cached app state."""
        self._refresh_from_app()

    def _refresh_from_app(self) -> None:
        """Pull latest backend data from the app cache into widgets."""
        app = self.app
        last_status = getattr(app, "_last_status", None)
        if last_status is None:
            return

        # Feed backends into health panel + server groups
        mgr = getattr(app, "_server_manager", None)
        if mgr is None:
            return
        client = getattr(mgr, "active_client", None)
        if client is None:
            return

        async def _fetch() -> None:
            try:
                backends_resp = await client.get_backends()
                details = [b.model_dump() for b in backends_resp.backends]
                try:
                    self.query_one(HealthPanel).update_from_backends(details)
                except Exception:
                    pass
                try:
                    self.query_one(ServerGroupsWidget).update_groups(details)
                except Exception:
                    pass
            except Exception:
                pass

        app.run_worker(_fetch(), exclusive=False, name="health-refresh")
