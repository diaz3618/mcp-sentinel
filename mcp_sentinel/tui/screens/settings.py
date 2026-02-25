"""Settings mode — theme picker, config viewer, and preferences."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static, TextArea

from mcp_sentinel.tui.screens.base import SentinelScreen

logger = logging.getLogger(__name__)


class SettingsScreen(SentinelScreen):
    """Settings mode — application configuration and theme management.

    Sub-sections:
    - Theme: current theme + button to open full picker
    - Config viewer: read-only view of the active config JSON
    - (Future) Auth, Secrets, Server Groups
    """

    def compose_content(self) -> ComposeResult:
        with Vertical(id="settings-layout"):
            yield Static("[b]Settings[/b]", id="settings-title")

            # ── Theme section ────────────────────────────────────
            with Horizontal(id="theme-section"):
                yield Static("Theme:", id="theme-label")
                yield Button("Open Theme Picker", id="btn-theme-picker", variant="primary")
                yield Button("Next Theme", id="btn-next-theme", variant="default")

            # ── Config viewer ────────────────────────────────────
            yield Static("[b]Active Configuration[/b]", id="config-title")
            yield TextArea(
                "",
                id="config-viewer",
                read_only=True,
                language="json",
            )

    def on_mount(self) -> None:
        """Populate config viewer on mount."""
        self._load_config_preview()

    def _load_config_preview(self) -> None:
        """Load the current config into the viewer."""
        import json as _json

        try:
            viewer = self.query_one("#config-viewer", TextArea)

            # Try to read from app's server manager if available
            sm = getattr(self.app, "server_manager", None)
            if sm is not None:
                servers = getattr(sm, "servers", None)
                if servers:
                    data = {}
                    for name, info in servers.items():
                        data[name] = {
                            "url": getattr(info, "url", str(info)),
                            "status": getattr(info, "status", "unknown"),
                        }
                    viewer.load_text(_json.dumps(data, indent=2))
                    return

            # Fallback: show helpful placeholder
            from mcp_sentinel.constants import DEFAULT_HOST, DEFAULT_PORT

            fallback = {
                "note": "Config viewer populated when connected to a server.",
                "default_host": DEFAULT_HOST,
                "default_port": DEFAULT_PORT,
            }
            viewer.load_text(_json.dumps(fallback, indent=2))
        except Exception:
            logger.debug("Could not load config preview", exc_info=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle settings button clicks."""
        if event.button.id == "btn-theme-picker":
            self.app.action_open_theme_picker()
        elif event.button.id == "btn-next-theme":
            self.app.action_next_theme()
