"""MCP Gateway Textual TUI application."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Dict, Optional

import uvicorn

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from mcp_gateway.constants import (
    AUTHOR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    SERVER_NAME,
    SERVER_VERSION,
)
from mcp_gateway.tui.events import CapabilitiesReady, ServerStopped, StatusUpdate
from mcp_gateway.tui.widgets.backend_status import BackendStatusWidget
from mcp_gateway.tui.widgets.capability_tables import CapabilitySection
from mcp_gateway.tui.widgets.event_log import EventLogWidget
from mcp_gateway.tui.widgets.server_info import ServerInfoWidget

logger = logging.getLogger(__name__)


class GatewayApp(App):
    """Textual TUI for the MCP Gateway server."""

    TITLE = f"{SERVER_NAME} v{SERVER_VERSION}"
    SUB_TITLE = f"by {AUTHOR}"
    CSS_PATH = "gateway.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("t", "show_tools", "Tools"),
        Binding("r", "show_resources", "Resources"),
        Binding("p", "show_prompts", "Prompts"),
        Binding("d", "toggle_dark", "Theme"),
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
            "Gateway TUI started — launching server…",
        )

        # Register the TUI callback so lifespan status updates reach us
        from mcp_gateway.display.console import set_status_callback

        set_status_callback(self._on_status_from_server)

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
                pass

    async def _server_main(self) -> None:
        """Async main running inside the server thread's event loop."""
        from mcp_gateway.display.logging_config import setup_logging
        from mcp_gateway.server.app import app

        log_fpath, cfg_log_lvl = setup_logging(self._log_level)

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
            cap.populate(tools, resources, prompts, route_map)

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
            pass

    def action_show_resources(self) -> None:
        """Switch capability table to Resources tab."""
        try:
            from textual.widgets import TabbedContent

            tabs = self.query_one("#cap-tabs", TabbedContent)
            tabs.active = "tab-resources"
        except Exception:
            pass

    def action_show_prompts(self) -> None:
        """Switch capability table to Prompts tab."""
        try:
            from textual.widgets import TabbedContent

            tabs = self.query_one("#cap-tabs", TabbedContent)
            tabs.active = "tab-prompts"
        except Exception:
            pass

    def action_quit(self) -> None:
        """Gracefully stop the server and exit the TUI."""
        event_log = self.query_one(EventLogWidget)
        event_log.add_event("🛑 Shutting Down", "User requested quit…")
        self._stop_server()
        self.exit()
