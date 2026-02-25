"""Tools mode — enhanced capability tables with filtering and search.

Provides a focused view of tools, resources, and prompts from all
connected backend servers.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.widgets.capability_tables import CapabilitySection


class ToolsScreen(SentinelScreen):
    """Tools mode — capability tables with search and filtering."""

    def compose_content(self) -> ComposeResult:
        yield Static(
            "[b]Tools Explorer[/b]  •  Browse, search, and inspect capabilities",
            id="tools-header",
        )
        yield CapabilitySection(id="tools-cap-section")
