"""Server information panel widget."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

logger = logging.getLogger(__name__)


class ServerInfoWidget(Widget):
    """Displays server metadata in a compact panel."""

    server_name: reactive[str] = reactive("MCP Sentinel")
    server_version: reactive[str] = reactive("")
    author: reactive[str] = reactive("")
    sse_url: reactive[str] = reactive("N/A")
    status_text: reactive[str] = reactive("Initializing…")

    # Kept internally for the command-palette detail view but not shown
    # in the sidebar panel.
    config_file: str = "N/A"
    log_file: str = "N/A"
    log_level: str = "INFO"

    def compose(self) -> ComposeResult:
        yield Static("", id="title-row")
        yield Static("", id="info-body")

    def _render_title(self) -> str:
        return f"{self.server_name} v{self.server_version}"

    def _render_body(self) -> str:
        lines = [
            f"[b]Author:[/b]  {self.author}",
            f"[b]SSE:[/b]     {self.sse_url}",
            "",
            f"[b]Status:[/b]  {self.status_text}",
        ]
        return "\n".join(lines)

    def _refresh_display(self) -> None:
        try:
            self.query_one("#title-row", Static).update(self._render_title())
            self.query_one("#info-body", Static).update(self._render_body())
        except Exception:
            logger.debug("ServerInfoWidget not yet mounted", exc_info=True)

    # Watchers – auto-refresh on any reactive change
    def watch_server_name(self) -> None:
        self._refresh_display()

    def watch_server_version(self) -> None:
        self._refresh_display()

    def watch_author(self) -> None:
        self._refresh_display()

    def watch_sse_url(self) -> None:
        self._refresh_display()

    def watch_status_text(self) -> None:
        self._refresh_display()

    def on_mount(self) -> None:
        self._refresh_display()

    # ── Public helpers ──────────────────────────────────────────

    def apply_status_info(self, info: dict) -> None:
        """Bulk-update from a ``gen_status_info`` dict."""
        import os

        if info.get("sse_url"):
            self.sse_url = info["sse_url"]
        if info.get("cfg_fpath"):
            self.config_file = os.path.basename(info["cfg_fpath"])
        if info.get("log_fpath"):
            self.log_file = info["log_fpath"]
        if info.get("log_lvl_cfg"):
            self.log_level = info["log_lvl_cfg"]
        if info.get("status_msg"):
            self.status_text = info["status_msg"]
