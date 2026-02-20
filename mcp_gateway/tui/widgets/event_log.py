"""Scrollable event log widget using RichLog."""

from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog

# Stage → colour mapping
_STAGE_COLOURS: dict[str, str] = {
    "🚀 Initialization": "bright_cyan",
    "📄 Config Load": "bright_blue",
    "🔌 Backend Connection": "bright_magenta",
    "🔍 Capability Discovery": "bright_yellow",
    "✅ Service Ready": "green",
    "❌ Startup Failed": "red",
    "🛑 Shutting Down": "dark_orange",
    "✅ Final Status": "green",
    "❌ Final Status": "red",
}


class EventLogWidget(Widget):
    """Real-time scrolling log of gateway lifecycle events."""

    BORDER_TITLE = "Events"

    def compose(self) -> ComposeResult:
        yield RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
            id="event-rich-log",
        )

    @property
    def log_widget(self) -> RichLog:
        return self.query_one("#event-rich-log", RichLog)

    # ── Public API ──────────────────────────────────────────────

    def add_event(
        self,
        stage: str,
        message: str,
        *,
        timestamp: str | None = None,
        extra_lines: list[str] | None = None,
    ) -> None:
        """Append a formatted event entry to the log."""
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        colour = _STAGE_COLOURS.get(stage, "white")

        header = Text.assemble(
            (f"[{ts}] ", "dim"),
            (f"{stage}: ", colour),
            (message, "bold"),
        )
        self.log_widget.write(header)

        if extra_lines:
            for line in extra_lines:
                indent = Text.assemble(("    ", ""), (line, ""))
                self.log_widget.write(indent)

    def add_raw(self, text: str) -> None:
        """Append a plain text line."""
        self.log_widget.write(text)

    def add_separator(self) -> None:
        """Write a visual separator."""
        self.log_widget.write(Text("─" * 60, style="dim"))
