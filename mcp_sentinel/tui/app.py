"""MCP Sentinel Textual TUI application.

Polls the management API of one or more running Sentinel servers over
HTTP via :class:`ServerManager`.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, Set

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from mcp_sentinel.constants import (
    AUTHOR,
    SERVER_NAME,
    SERVER_VERSION,
)
from mcp_sentinel.tui.events import (
    CapabilitiesReady,
    ConnectionLost,
    ConnectionRestored,
)
from mcp_sentinel.tui.screens.dashboard import DashboardScreen
from mcp_sentinel.tui.screens.registry import RegistryScreen
from mcp_sentinel.tui.screens.settings import SettingsScreen
from mcp_sentinel.tui.screens.theme_picker import ThemeScreen
from mcp_sentinel.tui.screens.tools import ToolsScreen
from mcp_sentinel.tui.widgets.backend_status import BackendStatusWidget
from mcp_sentinel.tui.widgets.capability_tables import CapabilitySection
from mcp_sentinel.tui.widgets.event_log import EventLogWidget
from mcp_sentinel.tui.widgets.server_info import ServerInfoWidget
from mcp_sentinel.tui.widgets.server_selector import ServerSelected, ServerSelectorWidget

logger = logging.getLogger(__name__)

# Polling interval for status updates (seconds).
_POLL_INTERVAL = 2.0

# Transport path suffixes that users might accidentally include in the
# ``--server`` URL.  We strip these so the management API client always
# targets the server root.
_TRANSPORT_SUFFIXES = ("/mcp", "/sse", "/messages/", "/messages")


def _normalise_server_url(url: str | None) -> str | None:
    """Strip transport-path suffixes from a server URL.

    Users may pass ``http://host:port/mcp`` as the ``--server`` URL, but
    the management API is mounted at ``/manage/v1`` on the server root.
    """
    if url is None:
        return None
    url = url.rstrip("/")
    for suffix in _TRANSPORT_SUFFIXES:
        if url.endswith(suffix):
            url = url[: -len(suffix)]
            break
    return url or None


class SentinelApp(App):
    """Textual TUI for the MCP Sentinel server."""

    TITLE = f"{SERVER_NAME} v{SERVER_VERSION}"
    SUB_TITLE = f"by {AUTHOR}"
    CSS_PATH = "sentinel.tcss"

    BINDINGS = [
        # ── App ────────────────────────────────────────────────
        Binding("q", "quit", "Quit", priority=True),
        # ── Mode switching ─────────────────────────────────────
        Binding("1", "switch_mode('dashboard')", "Dashboard", key_display="1"),
        Binding("d", "switch_mode('dashboard')", "Dashboard", show=False),
        Binding("2", "switch_mode('tools')", "Tools", key_display="2"),
        Binding("3", "switch_mode('registry')", "Registry", key_display="3"),
        Binding("4", "switch_mode('settings')", "Settings", key_display="4"),
        Binding("s", "switch_mode('settings')", "Settings", show=False),
        # ── Navigation (within active screen) ──────────────────
        Binding("t", "show_tools", "Tools Tab", show=False),
        Binding("r", "show_resources", "Resources Tab", show=False),
        Binding("p", "show_prompts", "Prompts Tab", show=False),
        # ── Theme ──────────────────────────────────────────────
        Binding("n", "next_theme", "Next Theme", show=False),
        Binding("T", "open_theme_picker", "Themes", key_display="shift+t", show=False),
    ]

    MODES = {
        "dashboard": DashboardScreen,
        "tools": ToolsScreen,
        "registry": RegistryScreen,
        "settings": SettingsScreen,
    }

    # ── Construction ────────────────────────────────────────────

    def __init__(
        self,
        server_url: Optional[str] = None,
        token: Optional[str] = None,
        *,
        server_manager: Optional[object] = None,
    ) -> None:
        super().__init__()

        # Remote mode parameters — normalise the URL so that the
        # management API client uses the server root, not an MCP
        # sub-path like /mcp or /sse.
        self._server_url = _normalise_server_url(server_url)
        self._token = token

        # Server manager — always used for connection management
        self._server_manager: Optional[object] = server_manager  # ServerManager

        # Polling state
        self._connected = False
        self._caps_loaded = False
        self._seen_event_ids: Set[str] = set()
        self._poll_timer: Optional[object] = None

        # Cached data for cross-screen access
        self._last_status: Optional[Any] = None
        self._last_caps: Optional[Any] = None

    # ── Compose (fallback — replaced immediately by default mode) ──

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    # ── System commands (Command Palette) ───────────────────────

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Extend the command palette with MCP Sentinel commands."""
        yield from super().get_system_commands(screen)

        # ── Modes ──────────────────────────────────────────────
        yield SystemCommand(
            title="Dashboard Mode",
            help="Server info, backends, events, and capabilities (1/d)",
            callback=lambda: self.switch_mode("dashboard"),
        )
        yield SystemCommand(
            title="Tools Mode",
            help="Full-screen capability explorer with filtering (2)",
            callback=lambda: self.switch_mode("tools"),
        )
        yield SystemCommand(
            title="Registry Mode",
            help="Server browser and discovery (3)",
            callback=lambda: self.switch_mode("registry"),
        )
        yield SystemCommand(
            title="Settings Mode",
            help="Theme, config viewer, and preferences (4/s)",
            callback=lambda: self.switch_mode("settings"),
        )

        # ── Server ─────────────────────────────────────────────
        yield SystemCommand(
            title="Show Server Details",
            help="Configuration file, log file, and log level",
            callback=self._show_server_details,
        )
        yield SystemCommand(
            title="Show Connection Info",
            help="SSE endpoint URL and backend status",
            callback=self._show_connection_info,
        )

        # ── Navigation ─────────────────────────────────────────
        yield SystemCommand(
            title="Show Tools Tab",
            help="Switch capability tables to the Tools tab",
            callback=self.action_show_tools,
        )
        yield SystemCommand(
            title="Show Resources Tab",
            help="Switch capability tables to the Resources tab",
            callback=self.action_show_resources,
        )
        yield SystemCommand(
            title="Show Prompts Tab",
            help="Switch capability tables to the Prompts tab",
            callback=self.action_show_prompts,
        )

        # ── Appearance ─────────────────────────────────────────
        yield SystemCommand(
            title="Open Theme Picker",
            help="Browse and preview all available themes",
            callback=self.action_open_theme_picker,
        )
        yield SystemCommand(
            title="Cycle Theme",
            help="Switch to the next enabled theme",
            callback=self.action_next_theme,
        )

    def _show_server_details(self) -> None:
        """Show server config details via notification."""
        try:
            srv = self.query_one(ServerInfoWidget)
            lines = [
                f"[b]Config file:[/b]  {srv.config_file}",
                f"[b]Log file:[/b]    {srv.log_file}",
                f"[b]Log level:[/b]   {srv.log_level}",
            ]
            self.notify("\n".join(lines), title="Server Details", timeout=8)
        except Exception:
            self.notify("Switch to Dashboard to view server details.", timeout=4)

    def action__tb_server_details(self) -> None:
        """Toolbar action: show server details notification."""
        self._show_server_details()

    def _show_connection_info(self) -> None:
        """Show connection info via notification."""
        try:
            srv = self.query_one(ServerInfoWidget)
            bk = self.query_one(BackendStatusWidget)
            lines = [
                f"[b]SSE URL:[/b]    {srv.sse_url}",
                f"[b]Backends:[/b]   {bk.connected}/{bk.total} connected",
                f"[b]Status:[/b]     {srv.status_text}",
            ]
            self.notify("\n".join(lines), title="Connection Info", timeout=8)
        except Exception:
            self.notify("Switch to Dashboard to view connection info.", timeout=4)

    # ── Lifecycle ───────────────────────────────────────────────

    def on_mount(self) -> None:
        """Called after the TUI is fully mounted."""
        # Load saved theme preference
        from mcp_sentinel.tui.settings import load_settings

        settings = load_settings()
        saved_theme = settings.get("theme", "textual-dark")
        if saved_theme in self.available_themes:
            self.theme = saved_theme

        # Ensure we have a ServerManager
        self._ensure_server_manager()

        # Switch to dashboard mode.  DashboardScreen.on_show() calls
        # _init_after_mode_switch() once widgets are ready; a deferred
        # timer provides a secondary fallback.
        self.switch_mode("dashboard")
        self.set_timer(0.3, self._init_after_mode_switch)

    def _init_after_mode_switch(self) -> None:
        """Initialize dashboard widgets after mode switch completes.

        Safe to call multiple times — becomes a no-op after the first
        successful run.
        """
        if getattr(self, "_dashboard_init_done", False):
            return
        try:
            info = self.query_one(ServerInfoWidget)
            info.server_name = SERVER_NAME
            info.server_version = SERVER_VERSION
            info.author = AUTHOR

            event_log = self.query_one(EventLogWidget)
            event_log.start_capture()

            self._start_remote_mode(info, event_log)
            self._dashboard_init_done = True
        except Exception:
            logger.warning("Dashboard initialization deferred", exc_info=True)

    def _ensure_server_manager(self) -> None:
        """Lazily create a :class:`ServerManager` if one wasn't injected."""
        if self._server_manager is not None:
            return

        from mcp_sentinel.tui.server_manager import ServerManager

        if self._server_url:
            # Single-server mode via --server URL
            self._server_manager = ServerManager.from_single(
                url=self._server_url, token=self._token
            )
        else:
            # Load from servers.json
            self._server_manager = ServerManager.from_config()

    def _start_remote_mode(self, info: ServerInfoWidget, event_log: EventLogWidget) -> None:
        """Initialize remote-mode: connect to server(s) via HTTP."""
        from mcp_sentinel.tui.server_manager import ServerManager

        mgr: ServerManager = self._server_manager  # type: ignore[assignment]

        if mgr.count == 0:
            # No servers configured — add a default
            from mcp_sentinel.constants import DEFAULT_HOST, DEFAULT_PORT

            default_url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
            mgr.add("local", default_url, set_active=True)
            mgr.save()

        active = mgr.active_entry
        if active:
            info.sse_url = active.url
            info.status_text = "Connecting…"
            event_log.add_event(
                "Initialization",
                f"Connecting to server '{active.name}' at {active.url}…",
            )
        else:
            info.status_text = "No servers configured"

        # Update the server selector widget
        self._refresh_server_selector()

        # Kick off the initial connection + polling
        self._start_polling()

    def on_unmount(self) -> None:
        """Clean up on app exit."""
        # Stop polling timer
        if self._poll_timer is not None:
            self._poll_timer.stop()

        # Close API clients via server manager
        if self._server_manager is not None:
            from mcp_sentinel.tui.server_manager import ServerManager

            if isinstance(self._server_manager, ServerManager):
                self.run_worker(self._server_manager.close_all(), exclusive=True)

        # Stop capturing print()
        try:
            self.query_one(EventLogWidget).stop_capture()
        except Exception:
            pass

    # ── Remote-mode polling ─────────────────────────────────────

    def _start_polling(self) -> None:
        """Begin the initial connection and periodic polling."""
        self._do_initial_connect()

    def _do_initial_connect(self) -> None:
        """Worker: establish the first connection to server(s)."""
        self.run_worker(self._initial_connect(), exclusive=True, name="initial-connect")

    async def _initial_connect(self) -> None:
        """Connect all servers via the manager and fetch initial state."""
        from mcp_sentinel.tui.server_manager import ServerManager

        mgr: ServerManager = self._server_manager  # type: ignore[assignment]

        results = await mgr.connect_all()
        for name, err in results.items():
            if err is None:
                logger.info("Connected to server '%s'", name)
            else:
                logger.warning("Failed to connect to '%s': %s", name, err)

        # Update selector after connect attempts
        self._refresh_server_selector()

        # Fetch state from the active server
        client = mgr.active_client
        if client is not None:
            try:
                health = await client.get_health()
                logger.info("Initial health check: %s", health.status)
                self._connected = True
                self.post_message(ConnectionRestored())

                status = await client.get_status()
                self._apply_status_response(status)

                caps = await client.get_capabilities()
                self._apply_capabilities_response(caps)
                self._caps_loaded = True

                events = await client.get_events(limit=50)
                self._apply_events_response(events)
            except Exception as exc:
                logger.warning("Initial data fetch failed: %s", exc)
                self.post_message(ConnectionLost(reason=f"Cannot reach server: {exc}"))
        else:
            active = mgr.active_entry
            reason = "No servers configured"
            if active:
                err = results.get(active.name)
                reason = f"Cannot reach server '{active.name}': {err}"
            self.post_message(ConnectionLost(reason=reason))

        # Start periodic polling regardless — it will retry on failure
        self._poll_timer = self.set_interval(_POLL_INTERVAL, self._poll_tick, name="status-poll")

    def _poll_tick(self) -> None:
        """Timer callback: dispatch async poll worker."""
        self.run_worker(self._poll_once(), exclusive=True, name="poll")

    async def _poll_once(self) -> None:
        """Single poll cycle: fetch status + events from active server."""
        from mcp_sentinel.tui.server_manager import ServerManager

        mgr: ServerManager = self._server_manager  # type: ignore[assignment]
        entry = mgr.active_entry
        if entry is None:
            return

        name = entry.name
        client = entry.client

        # Try to connect if not yet connected
        if client is None or not client.is_connected:
            try:
                await mgr.connect(name)
                client = mgr.active_client
            except Exception:
                return

        if client is None:
            return

        try:
            status = await client.get_status()
            self._apply_status_response(status)

            if not self._connected:
                self._connected = True
                self._caps_loaded = False
                mgr.mark_connected(name)
                self.post_message(ConnectionRestored())

            if not self._caps_loaded:
                caps = await client.get_capabilities()
                self._apply_capabilities_response(caps)
                self._caps_loaded = True

            events = await client.get_events(limit=20)
            self._apply_events_response(events)

            # Fetch backends for phase-aware status display
            try:
                backends_resp = await client.get_backends()
                self._apply_backends_response(backends_resp)
            except Exception:
                pass  # Non-critical — status poll already covers basics

        except Exception as exc:
            if self._connected:
                self._connected = False
                self._caps_loaded = False
                mgr.mark_disconnected(name)
                self.post_message(ConnectionLost(reason=str(exc)))

        # Refresh selector to reflect connection status changes
        self._refresh_server_selector()

    # ── Response → TUI message adapters ─────────────────────────

    def _apply_status_response(self, status: Any) -> None:
        """Convert a StatusResponse into widget updates."""
        self._last_status = status
        try:
            srv_widget = self.query_one(ServerInfoWidget)
            srv_widget.server_version = status.service.version or SERVER_VERSION
            srv_widget.sse_url = status.transport.sse_url or self._server_url or ""
            srv_widget.streamable_http_url = status.transport.streamable_http_url or ""
            if status.transport.streamable_http_url:
                srv_widget.transport_type = "streamable-http"
            srv_widget.status_text = status.service.state
            srv_widget.config_file = status.config.file_path or ""
        except Exception:
            pass  # Widget not in active screen

        try:
            backend = self.query_one(BackendStatusWidget)
            backend.total = status.config.backend_count
            if status.service.state == "running":
                backend.connected = status.config.backend_count
            elif status.service.state == "error":
                backend.connected = 0
        except Exception:
            pass  # Widget not in active screen

    def _apply_backends_response(self, backends_resp: Any) -> None:
        """Feed phase-aware backend data into BackendStatusWidget."""
        try:
            backend_widget = self.query_one(BackendStatusWidget)
            details = [b.model_dump() for b in backends_resp.backends]
            backend_widget.update_from_backends(details)
        except Exception:
            pass  # Widget not in active screen

    def _apply_capabilities_response(self, caps: Any) -> None:
        """Convert a CapabilitiesResponse into widget updates."""
        self._last_caps = caps

        # Convert Pydantic models to dicts for populate()
        tools = [t.model_dump() for t in caps.tools]
        resources = [r.model_dump() for r in caps.resources]
        prompts = [p.model_dump() for p in caps.prompts]
        route_map = caps.route_map

        try:
            cap_section = self.query_one(CapabilitySection)
            cap_section.populate(tools, resources, prompts, route_map)
        except Exception:
            pass  # Widget not in active screen

        try:
            event_log = self.query_one(EventLogWidget)
            event_log.add_event(
                "✅ Service Ready",
                f"{len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts loaded",
            )
        except Exception:
            pass  # Widget not in active screen

    def _apply_events_response(self, events_resp: Any) -> None:
        """Show new events in the EventLogWidget."""
        for ev in events_resp.events:
            if ev.id in self._seen_event_ids:
                continue
            self._seen_event_ids.add(ev.id)
            extra: list[str] = []
            if ev.details:
                for k, v in ev.details.items():
                    extra.append(f"{k}: {v}")
            try:
                event_log = self.query_one(EventLogWidget)
                event_log.add_event(
                    ev.stage,
                    ev.message,
                    timestamp=ev.timestamp,
                    extra_lines=extra if extra else None,
                )
            except Exception:
                pass  # Widget not in active screen

    # ── Server selector ───────────────────────────────────────────

    def _refresh_server_selector(self) -> None:
        """Update the ServerSelectorWidget with current server entries."""
        from mcp_sentinel.tui.server_manager import ServerManager

        mgr: Optional[ServerManager] = self._server_manager  # type: ignore[assignment]
        if mgr is None:
            return

        try:
            selector = self.query_one("#srv-selector", ServerSelectorWidget)
        except Exception:
            return  # widget not mounted yet

        servers = [
            {
                "name": e.name,
                "url": e.url,
                "connected": e.connected,
            }
            for e in mgr.entries.values()
        ]
        selector.refresh_servers(servers, active_name=mgr.active_name)

    def on_server_selected(self, event: ServerSelected) -> None:
        """Handle the user switching to a different server."""
        from mcp_sentinel.tui.server_manager import ServerManager

        mgr: Optional[ServerManager] = self._server_manager  # type: ignore[assignment]
        if mgr is None:
            return

        name = event.server_name
        logger.info("Switching active server to '%s'", name)

        mgr.set_active(name)
        mgr.save()

        # Reset state for the new server
        self._connected = False
        self._caps_loaded = False
        self._seen_event_ids.clear()

        # Update the info panel
        entry = mgr.active_entry
        if entry:
            try:
                srv_widget = self.query_one(ServerInfoWidget)
                srv_widget.sse_url = entry.url
                srv_widget.status_text = "Connecting\u2026" if not entry.connected else "Connected"
            except Exception:
                pass

            try:
                event_log = self.query_one(EventLogWidget)
                event_log.add_event(
                    "Server Switch",
                    f"Switched to '{name}' ({entry.url})",
                )
            except Exception:
                pass

        # Force an immediate poll
        self.run_worker(self._poll_once(), exclusive=True, name="poll-switch")

        # Refresh selector display
        self._refresh_server_selector()

    # ── Message handlers ────────────────────────────────────────

    def on_capabilities_ready(self, event: CapabilitiesReady) -> None:
        """Explicit capability population (alternative path)."""
        cap = self.query_one(CapabilitySection)
        cap.populate(
            event.tools,
            event.resources,
            event.prompts,
            event.route_map,
        )

    def on_connection_lost(self, event: ConnectionLost) -> None:
        """Handle loss of HTTP connection to the remote server."""
        srv_widget = self.query_one(ServerInfoWidget)
        srv_widget.status_text = "Disconnected"

        event_log = self.query_one(EventLogWidget)
        event_log.add_event(
            "⚠️  Connection Lost",
            event.reason,
        )
        self.notify(
            f"Connection lost: {event.reason}",
            title="Disconnected",
            severity="warning",
            timeout=5,
        )

    def on_connection_restored(self, event: ConnectionRestored) -> None:
        """Handle reconnection to the remote server."""
        srv_widget = self.query_one(ServerInfoWidget)
        srv_widget.status_text = "Connected"

        event_log = self.query_one(EventLogWidget)
        event_log.add_event(
            "✅ Reconnected",
            "Connection to server restored.",
        )

    # ── Key-bound actions ───────────────────────────────────────

    def action_show_tools(self) -> None:
        """Switch capability table to Tools tab."""
        try:
            from textual.widgets import TabbedContent

            tabs = self.query_one("#cap-tabs", TabbedContent)
            tabs.active = "tab-tools"
        except Exception:
            logger.debug("Could not switch to tools tab", exc_info=True)

    def action_show_resources(self) -> None:
        """Switch capability table to Resources tab."""
        try:
            from textual.widgets import TabbedContent

            tabs = self.query_one("#cap-tabs", TabbedContent)
            tabs.active = "tab-resources"
        except Exception:
            logger.debug("Could not switch to resources tab", exc_info=True)

    def action_show_prompts(self) -> None:
        """Switch capability table to Prompts tab."""
        try:
            from textual.widgets import TabbedContent

            tabs = self.query_one("#cap-tabs", TabbedContent)
            tabs.active = "tab-prompts"
        except Exception:
            logger.debug("Could not switch to prompts tab", exc_info=True)

    def action_quit(self) -> None:
        """Gracefully exit the TUI."""
        try:
            event_log = self.query_one(EventLogWidget)
            event_log.add_event("🛑 Shutting Down", "User requested quit…")
        except Exception:
            pass
        self.exit()

    def action_next_theme(self) -> None:
        """Cycle to the next enabled theme and persist the choice."""
        from mcp_sentinel.tui.settings import load_settings, save_settings

        settings = load_settings()
        enabled = settings.get("enabled_themes", ["textual-dark"])
        # Filter to themes actually registered
        enabled = [t for t in enabled if t in self.available_themes]
        if not enabled:
            enabled = ["textual-dark"]

        current = self.theme or "textual-dark"
        try:
            idx = enabled.index(current)
            next_theme = enabled[(idx + 1) % len(enabled)]
        except ValueError:
            next_theme = enabled[0]

        self.theme = next_theme
        settings["theme"] = next_theme
        save_settings(settings)

        self.notify(f"Theme: {next_theme}", timeout=2)

    def action_open_theme_picker(self) -> None:
        """Open the modal theme picker screen."""

        def _on_theme_selected(theme_name: str | None) -> None:
            if theme_name is not None:
                from mcp_sentinel.tui.settings import load_settings, save_settings

                settings = load_settings()
                settings["theme"] = theme_name
                save_settings(settings)
                self.notify(f"Theme: {theme_name}", timeout=2)

        self.push_screen(ThemeScreen(), _on_theme_selected)
