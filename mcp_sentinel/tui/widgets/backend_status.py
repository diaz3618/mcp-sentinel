"""Backend connection status widget."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

logger = logging.getLogger(__name__)

# Phase → (icon, color)
_PHASE_STYLE: Dict[str, tuple] = {
    "pending": ("◌", "$text-muted"),
    "initializing": ("◑", "yellow"),
    "ready": ("●", "green"),
    "degraded": ("●", "dark_orange"),
    "failed": ("✕", "red"),
    "shutting_down": ("◑", "cyan"),
}


class BackendStatusWidget(Widget):
    """Compact bar showing per-backend lifecycle phases."""

    connected: reactive[int] = reactive(0)
    total: reactive[int] = reactive(0)
    backend_details: reactive[list] = reactive(list, always_update=True)

    def compose(self) -> ComposeResult:
        yield Static("Backend Services", id="backend-title")
        yield Static("", id="backend-bar")
        yield Static("", id="backend-detail")

    def update_from_backends(self, backends: List[Dict[str, Any]]) -> None:
        """Populate widget from management API backend list."""
        self.backend_details = backends
        self.total = len(backends)
        self.connected = sum(1 for b in backends if b.get("phase") in ("ready", "degraded"))

    def _refresh_display(self) -> None:
        try:
            details = self.backend_details
            if details:
                # Render per-backend phase lines
                lines: list[str] = []
                for b in details:
                    phase = b.get("phase", "pending")
                    icon, color = _PHASE_STYLE.get(phase, ("?", "$text-muted"))
                    name = b.get("name", "?")
                    latency = b.get("last_latency_ms")
                    lat_str = f" {latency:.0f}ms" if latency else ""
                    error = b.get("error", "")
                    err_str = f' "{error}"' if error and phase == "failed" else ""
                    lines.append(
                        f"[{color}]{icon}[/{color}] {name:<20} "
                        f"[{color}]{phase.title():<14}[/{color}]"
                        f"{lat_str}{err_str}"
                    )
                bar_text = "\n".join(lines)
            else:
                # Fallback: simple connected / total bar
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

    def watch_backend_details(self) -> None:
        self._refresh_display()

    def on_mount(self) -> None:
        self._refresh_display()
