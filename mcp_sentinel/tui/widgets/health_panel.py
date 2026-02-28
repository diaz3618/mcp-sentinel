"""Health checks & circuit breaker widget.

Displays per-backend health indicators, circuit-breaker state,
probe history, and latency. Can be shown in backend detail or as
a standalone panel.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static

logger = logging.getLogger(__name__)

# Map circuit state to display
_CIRCUIT_DISPLAY = {
    "closed": "[green]CLOSED[/green]",
    "open": "[red]OPEN[/red]",
    "half-open": "[yellow]HALF-OPEN[/yellow]",
}


class HealthPanel(Widget):
    """Shows backend health status, circuit breaker state, and latency.

    Feed data via :meth:`update_from_backends` with a list of backend
    dicts (from the management API ``/manage/v1/backends`` response).
    """

    DEFAULT_CSS = """
    HealthPanel {
        height: auto;
        max-height: 20;
        border: round $accent;
        padding: 0 1;
    }
    #health-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 0;
    }
    #health-summary {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    #health-table {
        height: auto;
        max-height: 10;
    }
    #circuit-breaker-info {
        height: auto;
        max-height: 4;
        padding: 0 1;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[b]Health Status[/b]", id="health-title")
            yield Static("Healthy: 0  Degraded: 0  Unhealthy: 0", id="health-summary")
            yield DataTable(id="health-table")
            yield Static("", id="circuit-breaker-info")

    def on_mount(self) -> None:
        try:
            table = self.query_one("#health-table", DataTable)
            table.add_columns("Server", "State", "Circuit", "Last Ping", "Latency")
            table.cursor_type = "row"
            table.zebra_stripes = True
        except Exception:
            pass

    def update_from_backends(self, backends: List[Dict[str, Any]]) -> None:
        """Refresh the health table from backend data."""
        try:
            table = self.query_one("#health-table", DataTable)
            table.clear()

            healthy = degraded = unhealthy = 0
            circuit_info_lines = []

            for b in backends:
                name = b.get("name", "?")
                phase = b.get("phase", "unknown").lower()
                health = b.get("health", {})
                health_status = health.get("status", "unknown") if health else "unknown"
                last_check = health.get("last_check", "—") if health else "—"
                latency = health.get("latency_ms") if health else None
                lat_str = f"{latency:.0f}ms" if latency else "—"
                circuit = b.get("circuit_state", "closed")

                # Count by health status
                if phase == "ready" or health_status == "healthy":
                    healthy += 1
                    state_display = "[green]● healthy[/green]"
                elif phase == "degraded" or health_status == "degraded":
                    degraded += 1
                    state_display = "[yellow]◑ degraded[/yellow]"
                else:
                    unhealthy += 1
                    state_display = "[red]✕ unhealthy[/red]"

                circuit_display = _CIRCUIT_DISPLAY.get(circuit, f"[dim]{circuit}[/dim]")

                # Trim timestamps
                if isinstance(last_check, str) and "T" in last_check:
                    last_check = last_check.split("T")[1][:8]

                table.add_row(name, state_display, circuit_display, str(last_check), lat_str)

                # Circuit breaker detail for open/half-open
                if circuit and circuit != "closed":
                    failures = b.get("failure_count", "?")
                    cooldown = b.get("cooldown_remaining", "?")
                    circuit_info_lines.append(
                        f"  {name}: {circuit.upper()} — {failures} failures, cooldown: {cooldown}s"
                    )

            summary = f"Healthy: {healthy}   Degraded: {degraded}   Unhealthy: {unhealthy}"
            self.query_one("#health-summary", Static).update(summary)

            if circuit_info_lines:
                self.query_one("#circuit-breaker-info", Static).update(
                    "[b]Circuit Breakers:[/b]\n" + "\n".join(circuit_info_lines)
                )
            else:
                self.query_one("#circuit-breaker-info", Static).update("")

        except Exception:
            logger.debug("Cannot update health panel", exc_info=True)
