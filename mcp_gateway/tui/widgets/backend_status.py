"""Backend connection status widget."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

logger = logging.getLogger(__name__)


class BackendStatusWidget(Widget):
    """Compact bar showing connected / total backend services."""

    connected: reactive[int] = reactive(0)
    total: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("Backend Services", id="backend-title")
        yield Static("", id="backend-bar")
        yield Static("", id="backend-detail")

    def _refresh_display(self) -> None:
        try:
            # Visual bar: ● for connected, ○ for disconnected
            bar_parts: list[str] = []
            for i in range(self.total):
                if i < self.connected:
                    bar_parts.append("[green]●[/green]")
                else:
                    bar_parts.append("[red]○[/red]")
            bar_text = " ".join(bar_parts) if bar_parts else "—"

            if self.total == 0:
                detail = "No backends configured"
                color = "$text-muted"
            elif self.connected == self.total:
                detail = f"All {self.total} connected"
                color = "green"
            elif self.connected == 0:
                detail = f"0 / {self.total} connected"
                color = "red"
            else:
                detail = f"{self.connected} / {self.total} connected"
                color = "yellow"

            self.query_one("#backend-bar", Static).update(bar_text)
            self.query_one("#backend-detail", Static).update(f"[{color}]{detail}[/{color}]")
        except Exception:
            logger.debug("BackendStatusWidget not yet mounted", exc_info=True)

    def watch_connected(self) -> None:
        self._refresh_display()

    def watch_total(self) -> None:
        self._refresh_display()

    def on_mount(self) -> None:
        self._refresh_display()
