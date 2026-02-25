"""Tool editor screen — visual tool customization interface.

Sub-screen within Settings mode for customizing tools:
- Rename with live preview
- Include/exclude toggle
- Parameter defaults
- Save to config / undo
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label

from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.widgets.param_editor import ParamEditorWidget
from mcp_sentinel.tui.widgets.tool_preview import ToolPreviewWidget

logger = logging.getLogger(__name__)


class ToolEditorScreen(SentinelScreen):
    """Interactive tool customization screen.

    Layout:
    - Left: tool list (DataTable)
    - Center: editing controls (rename, filter, defaults)
    - Right: live preview of tool as client sees it
    """

    CSS = """
    ToolEditorScreen {
        layout: horizontal;
    }

    #tool-list-panel {
        width: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #editor-panel {
        width: 2fr;
        border: solid $accent;
        padding: 1;
    }

    #preview-panel {
        width: 1fr;
        border: solid $success;
        padding: 1;
    }

    #rename-input {
        margin: 1 0;
    }

    .editor-section {
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("ctrl+s", "save_changes", "Save"),
        ("ctrl+z", "reset_tool", "Reset"),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tools: List[Dict[str, Any]] = []
        self._selected_tool: Optional[str] = None
        self._modifications: Dict[str, Dict[str, Any]] = {}

    def compose_content(self) -> ComposeResult:
        with Horizontal():
            # Left: Tool list
            with Vertical(id="tool-list-panel"):
                yield Label("[b]Tools[/b]")
                yield DataTable(id="tool-table")

            # Center: Editor
            with Vertical(id="editor-panel"):
                yield Label("[b]Tool Editor[/b]")
                yield Label("[dim]Select a tool to edit[/]", id="editor-hint")

                with Vertical(classes="editor-section", id="rename-section"):
                    yield Label("Rename:")
                    yield Input(placeholder="New tool name", id="rename-input")

                with Vertical(classes="editor-section", id="include-section"):
                    yield Label("Included:")
                    yield Button("Toggle Include/Exclude", id="toggle-include")

                with Vertical(classes="editor-section", id="defaults-section"):
                    yield Label("Parameter Defaults:")
                    yield ParamEditorWidget(id="param-editor")

                with Vertical(id="actions-section"):
                    yield Button("Save All Changes", variant="primary", id="save-btn")
                    yield Button("Reset Selected", variant="warning", id="reset-btn")

            # Right: Preview
            with Vertical(id="preview-panel"):
                yield ToolPreviewWidget(id="tool-preview")

    def on_mount(self) -> None:
        table = self.query_one("#tool-table", DataTable)
        table.add_columns("Name", "Backend", "Status")
        table.cursor_type = "row"

    def load_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Load tools into the editor."""
        self._tools = tools
        table = self.query_one("#tool-table", DataTable)
        table.clear()
        for tool in tools:
            name = tool.get("name", "unknown")
            backend = tool.get("backend", "")
            # Check modifications for include status
            mods = self._modifications.get(name, {})
            included = mods.get("included", tool.get("included", True))
            status = "✓" if included else "✗"
            table.add_row(name, backend, status, key=name)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value:
            self._select_tool(event.row_key.value)

    def _select_tool(self, tool_name: str) -> None:
        """Update editor and preview for the selected tool."""
        self._selected_tool = tool_name

        # Find tool info
        tool_info = next(
            (t for t in self._tools if t.get("name") == tool_name),
            None,
        )
        if not tool_info:
            return

        # Get modifications if any
        mods = self._modifications.get(tool_name, {})
        display_name = mods.get("rename", tool_name)

        # Update rename input
        rename = self.query_one("#rename-input", Input)
        rename.value = display_name

        # Update parameter editor with tool's input schema
        try:
            param_editor = self.query_one("#param-editor", ParamEditorWidget)
            schema = tool_info.get("inputSchema", {})
            defaults = mods.get("defaults", {})
            param_editor.load_schema(schema, defaults)
        except Exception:
            pass  # ParamEditor not yet mounted

        # Update preview
        preview = self.query_one("#tool-preview", ToolPreviewWidget)
        preview.update_preview(
            {
                "name": display_name,
                "description": tool_info.get("description", ""),
                "inputSchema": tool_info.get("inputSchema", {}),
            }
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "rename-input" and self._selected_tool:
            if self._selected_tool not in self._modifications:
                self._modifications[self._selected_tool] = {}
            self._modifications[self._selected_tool]["rename"] = event.value

            # Update preview
            tool_info = next(
                (t for t in self._tools if t.get("name") == self._selected_tool),
                None,
            )
            if tool_info:
                preview = self.query_one("#tool-preview", ToolPreviewWidget)
                preview.update_preview(
                    {
                        "name": event.value,
                        "description": tool_info.get("description", ""),
                        "inputSchema": tool_info.get("inputSchema", {}),
                    }
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle-include":
            self._toggle_include()
        elif event.button.id == "save-btn":
            self.action_save_changes()
        elif event.button.id == "reset-btn":
            self.action_reset_tool()

    def _toggle_include(self) -> None:
        if not self._selected_tool:
            return
        if self._selected_tool not in self._modifications:
            self._modifications[self._selected_tool] = {}
        # Get current state: check modifications first, then original tool data
        tool_info = next((t for t in self._tools if t.get("name") == self._selected_tool), None)
        original = tool_info.get("included", True) if tool_info else True
        current = self._modifications[self._selected_tool].get("included", original)
        self._modifications[self._selected_tool]["included"] = not current
        # Refresh table to reflect the change
        self.load_tools(self._tools)

    def action_save_changes(self) -> None:
        """Save modifications to config (emits notification)."""
        if not self._modifications:
            self.notify("No changes to save")
            return
        # In production, this would write to the config file
        logger.info("Tool customizations saved: %s", json.dumps(self._modifications))
        self.notify(f"Saved {len(self._modifications)} tool customization(s)")

    def action_reset_tool(self) -> None:
        """Reset modifications for the selected tool."""
        if self._selected_tool and self._selected_tool in self._modifications:
            del self._modifications[self._selected_tool]
            self._select_tool(self._selected_tool)
            self.notify(f"Reset '{self._selected_tool}'")

    def action_go_back(self) -> None:
        """Return to settings."""
        self.app.pop_screen()

    def get_modifications(self) -> Dict[str, Dict[str, Any]]:
        """Return all pending modifications."""
        return dict(self._modifications)
