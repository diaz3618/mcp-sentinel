"""Server information panel widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class ServerInfoWidget(Widget):
    """Displays gateway server metadata in a compact panel."""

    server_name: reactive[str] = reactive("MCP_Gateway")
    server_version: reactive[str] = reactive("")
    author: reactive[str] = reactive("")
    sse_url: reactive[str] = reactive("N/A")
    config_file: reactive[str] = reactive("N/A")
    log_file: reactive[str] = reactive("N/A")
    log_level: reactive[str] = reactive("INFO")
    status_text: reactive[str] = reactive("Initializing…")

    def compose(self) -> ComposeResult:
        yield Static("", id="title-row")
        yield Static("", id="info-body")

    def _render_title(self) -> str:
        return f"{self.server_name} v{self.server_version}"

    def _render_body(self) -> str:
        lines = [
            f"[b]Author:[/b]      {self.author}",
            f"[b]SSE URL:[/b]    {self.sse_url}",
            f"[b]Config:[/b]     {self.config_file}",
            f"[b]Log file:[/b]   {self.log_file}",
            f"[b]Log level:[/b]  {self.log_level}",
            "",
            f"[b]Status:[/b]     {self.status_text}",
        ]
        return "\n".join(lines)

    def _refresh_display(self) -> None:
        try:
            self.query_one("#title-row", Static).update(self._render_title())
            self.query_one("#info-body", Static).update(self._render_body())
        except Exception:
            pass  # widget not yet mounted

    # Watchers – auto-refresh on any reactive change
    def watch_server_name(self) -> None:
        self._refresh_display()

    def watch_server_version(self) -> None:
        self._refresh_display()

    def watch_author(self) -> None:
        self._refresh_display()

    def watch_sse_url(self) -> None:
        self._refresh_display()

    def watch_config_file(self) -> None:
        self._refresh_display()

    def watch_log_file(self) -> None:
        self._refresh_display()

    def watch_log_level(self) -> None:
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
