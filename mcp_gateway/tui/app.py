"""MCP Sentinel Textual TUI application."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Dict, Iterable, Optional

import uvicorn
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header

from mcp_gateway.constants import (
    AUTHOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from mcp_gateway.tui.events import CapabilitiesReady, ServerStopped, StatusUpdate
from mcp_gateway.tui.screens.theme_picker import ThemeScreen
from mcp_gateway.tui.widgets.backend_status import BackendStatusWidget
from mcp_gateway.tui.widgets.capability_tables import CapabilitySection
from mcp_gateway.tui.widgets.event_log import EventLogWidget
from mcp_gateway.tui.widgets.server_info import ServerInfoWidget

logger = logging.getLogger(__name__)


class GatewayApp(App):
    """Textual TUI for the MCP Sentinel server."""

    TITLE = f"{SERVER_NAME} v{SERVER_VERSION}"
    SUB_TITLE = f"by {AUTHOR}"
    CSS_PATH = "gateway.tcss"

    BINDINGS = [
        # ── App ────────────────────────────────────────────────
        Binding("q", "quit", "Quit", priority=True),
        # ── Navigation ─────────────────────────────────────────
        Binding("t", "show_tools", "Tools"),
        Binding("r", "show_resources", "Resources"),
        Binding("p", "show_prompts", "Prompts"),
        # ── Theme ──────────────────────────────────────────────
        Binding("n", "next_theme", "Next Theme"),
        Binding("T", "open_theme_picker", "Themes", key_display="shift+t"),
    ]

    # ── Construction ────────────────────────────────────────────

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        log_level: str = "info",
    ) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._log_level = log_level
        self._server_thread: Optional[threading.Thread] = None
        self._uvicorn_server: Optional[uvicorn.Server] = None

    # ── Compose ─────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-row"):
            with Vertical(id="sidebar"):
                yield ServerInfoWidget()
                yield BackendStatusWidget()
            with Vertical(id="main-area"):
                yield EventLogWidget()
        yield CapabilitySection(id="cap-section")
        yield Footer()

    # ── System commands (Command Palette) ───────────────────────

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Extend the command palette with MCP Sentinel commands."""
        yield from super().get_system_commands(screen)

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
        srv = self.query_one(ServerInfoWidget)
        lines = [
            f"[b]Config file:[/b]  {srv.config_file}",
            f"[b]Log file:[/b]    {srv.log_file}",
            f"[b]Log level:[/b]   {srv.log_level}",
        ]
        self.notify("\n".join(lines), title="Server Details", timeout=8)

    def _show_connection_info(self) -> None:
        """Show connection info via notification."""
        srv = self.query_one(ServerInfoWidget)
        bk = self.query_one(BackendStatusWidget)
        lines = [
            f"[b]SSE URL:[/b]    {srv.sse_url}",
            f"[b]Backends:[/b]   {bk.connected}/{bk.total} connected",
            f"[b]Status:[/b]     {srv.status_text}",
        ]
        self.notify("\n".join(lines), title="Connection Info", timeout=8)

    # ── Lifecycle ───────────────────────────────────────────────

    def on_mount(self) -> None:
        """Called after the TUI is fully mounted."""
        info = self.query_one(ServerInfoWidget)
        info.server_name = SERVER_NAME
        info.server_version = SERVER_VERSION
        info.author = AUTHOR
        info.sse_url = f"http://{self._host}:{self._port}/sse"
        info.status_text = "Starting…"

        event_log = self.query_one(EventLogWidget)
        event_log.add_event(
            "🚀 Initialization",
            "Sentinel TUI started — launching server…",
        )

        # Register the TUI callback so lifespan status updates reach us
        from mcp_gateway.display.console import set_status_callback

        set_status_callback(self._on_status_from_server)

        # --- Stdout / stderr isolation ---
        # Use the canonical Textual pattern: call begin_capture_print()
        # on the RichLog widget inside EventLogWidget so that stray
        # print() calls from libraries/uvicorn appear in the Events panel
        # instead of corrupting the TUI terminal.
        event_log.start_capture()

        # NOTE: We intentionally do NOT redirect fd 2 (stderr).
        # Textual's LinuxDriver renders the entire TUI via
        # sys.__stderr__ (fd 2).  Redirecting it to /dev/null
        # causes a completely blank screen.  The begin_capture_print()
        # call above already intercepts Python-level print() calls;
        # any remaining C-level noise on stderr is acceptable.

        # Load saved theme preference
        from mcp_gateway.tui.settings import load_settings

        settings = load_settings()
        saved_theme = settings.get("theme", "textual-dark")
        if saved_theme in self.available_themes:
            self.theme = saved_theme

        # Launch the uvicorn server in a daemon thread
        self._server_thread = threading.Thread(
            target=self._run_server,
            name="uvicorn-server",
            daemon=True,
        )
        self._server_thread.start()

    def on_unmount(self) -> None:
        """Clean up on app exit."""
        from mcp_gateway.display.console import clear_status_callback

        clear_status_callback()
        self._stop_server()

        # Stop capturing print()
        try:
            self.query_one(EventLogWidget).stop_capture()
        except Exception:
            pass

    # ── Server thread ───────────────────────────────────────────

    def _run_server(self) -> None:
        """Entry-point for the daemon server thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        error_msg: Optional[str] = None
        try:
            loop.run_until_complete(self._server_main())
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception("Server thread error")
        finally:
            loop.close()
            # Notify the TUI (thread-safe)
            try:
                self.call_from_thread(
                    self.post_message, ServerStopped(error=error_msg)
                )
            except Exception:
                logger.debug("Failed to post ServerStopped", exc_info=True)

    async def _server_main(self) -> None:
        """Async main running inside the server thread's event loop."""
        from mcp_gateway.display.logging_config import setup_logging
        from mcp_gateway.server.app import app

        log_fpath, cfg_log_lvl = setup_logging(self._log_level, quiet=True)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(script_dir))
        cfg_abs_path = os.path.join(project_dir, "config.json")

        app_s = app.state
        app_s.host = self._host
        app_s.port = self._port
        app_s.actual_log_file = log_fpath
        app_s.file_log_level_configured = cfg_log_lvl
        app_s.config_file_path = cfg_abs_path

        uvicorn_cfg = uvicorn.Config(
            app="mcp_gateway.server.app:app",
            host=self._host,
            port=self._port,
            log_config=None,
            log_level=(
                cfg_log_lvl.lower() if cfg_log_lvl == "DEBUG" else "warning"
            ),
        )
        self._uvicorn_server = uvicorn.Server(uvicorn_cfg)
        await self._uvicorn_server.serve()

    def _stop_server(self) -> None:
        """Signal the uvicorn server to shut down."""
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True

    # ── Status callback (called from server thread) ─────────────

    def _on_status_from_server(
        self,
        stage: str,
        status_info: Dict[str, Any],
        is_final: bool,
    ) -> None:
        """Thread-safe bridge: server thread → TUI message."""
        try:
            self.call_from_thread(
                self.post_message,
                StatusUpdate(stage, status_info, is_final),
            )
        except Exception:
            pass  # app may already be exiting

    # ── Message handlers ────────────────────────────────────────

    def on_status_update(self, event: StatusUpdate) -> None:
        """Process a gateway lifecycle status update."""
        info = event.status_info
        stage = event.stage

        # Update server info panel
        srv_widget = self.query_one(ServerInfoWidget)
        srv_widget.apply_status_info(info)

        # Update backend status
        backend = self.query_one(BackendStatusWidget)
        if "conn_svrs_num" in info:
            backend.connected = info["conn_svrs_num"]
        if "total_svrs_num" in info:
            backend.total = info["total_svrs_num"]

        # Append to event log
        event_log = self.query_one(EventLogWidget)
        extra: list[str] = []
        if "conn_svrs_num" in info and "total_svrs_num" in info:
            extra.append(
                f"Backend Services: {info['conn_svrs_num']} / "
                f"{info['total_svrs_num']} connected"
            )
        if "tools_count" in info:
            extra.append(f"MCP Tools: {info['tools_count']} loaded")
        if "resources_count" in info:
            extra.append(f"MCP Resources: {info['resources_count']} loaded")
        if "prompts_count" in info:
            extra.append(f"MCP Prompts: {info['prompts_count']} loaded")
        if info.get("err_msg"):
            extra.append(f"!! Error: {info['err_msg']}")

        event_log.add_event(
            stage,
            info.get("status_msg", ""),
            timestamp=info.get("ts"),
            extra_lines=extra if extra else None,
        )

        if event.is_final:
            event_log.add_separator()

        # Populate capability tables when ready
        if stage == "✅ Service Ready":
            cap = self.query_one(CapabilitySection)
            tools = info.get("tools", [])
            resources = info.get("resources", [])
            prompts = info.get("prompts", [])
            route_map = info.get("route_map", {})
            logger.info(
                "Populating TUI tables: %d tools, %d resources, %d prompts",
                len(tools), len(resources), len(prompts),
            )
            try:
                cap.populate(
                    list(tools), list(resources), list(prompts), route_map,
                )
            except Exception:
                logger.exception("Error populating capability tables")

    def on_capabilities_ready(self, event: CapabilitiesReady) -> None:
        """Explicit capability population (alternative path)."""
        cap = self.query_one(CapabilitySection)
        cap.populate(
            event.tools,
            event.resources,
            event.prompts,
            event.route_map,
        )

    def on_server_stopped(self, event: ServerStopped) -> None:
        """Handle uvicorn server thread exit."""
        event_log = self.query_one(EventLogWidget)
        if event.error:
            event_log.add_event(
                "❌ Server Error",
                f"Server thread exited with error: {event.error}",
            )
        else:
            event_log.add_event(
                "✅ Final Status",
                "Server thread exited normally.",
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
        """Gracefully stop the server and exit the TUI."""
        event_log = self.query_one(EventLogWidget)
        event_log.add_event("🛑 Shutting Down", "User requested quit…")
        self._stop_server()
        self.exit()

    def action_next_theme(self) -> None:
        """Cycle to the next enabled theme and persist the choice."""
        from mcp_gateway.tui.settings import load_settings, save_settings

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
                from mcp_gateway.tui.settings import load_settings, save_settings

                settings = load_settings()
                settings["theme"] = theme_name
                save_settings(settings)
                self.notify(f"Theme: {theme_name}", timeout=2)

        self.push_screen(ThemeScreen(), _on_theme_selected)
