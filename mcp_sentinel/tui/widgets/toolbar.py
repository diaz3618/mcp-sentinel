"""Categorized action toolbar for the TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label


class _ToolbarAction(Label):
    """A single clickable action label inside the toolbar."""

    DEFAULT_CSS = """
    _ToolbarAction {
        padding: 0 1;
        color: $text;
    }
    _ToolbarAction:hover {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, text: str, action: str, **kwargs: object) -> None:
        super().__init__(text, **kwargs)
        self._action_name = action

    async def on_click(self) -> None:
        """Dispatch the bound action on the app."""
        await self.app.run_action(self._action_name)


class _ToolbarSep(Label):
    """Visual separator between toolbar groups."""

    DEFAULT_CSS = """
    _ToolbarSep {
        color: $text-muted;
        padding: 0;
    }
    """

    def __init__(self) -> None:
        super().__init__(" │ ")


class ToolbarWidget(Widget):
    """Horizontal categorized toolbar docked to the top of the app.

    Groups:
    - **Server**: Quit, Details
    - **Navigate**: Tools, Resources, Prompts
    - **Appearance**: Themes, Next Theme
    """

    DEFAULT_CSS = """
    ToolbarWidget {
        dock: top;
        height: 1;
        width: 100%;
        background: $panel;
        layout: horizontal;
        padding: 0 1;
    }
    ToolbarWidget ._cat-label {
        color: $accent;
        text-style: bold;
        padding: 0 0 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        # ── Server ──
        yield Label(" Server: ", classes="_cat-label")
        yield _ToolbarAction("Quit", "quit")
        yield _ToolbarAction("Details", "_tb_server_details")
        yield _ToolbarSep()

        # ── Navigate ──
        yield Label("Navigate: ", classes="_cat-label")
        yield _ToolbarAction("Tools", "show_tools")
        yield _ToolbarAction("Resources", "show_resources")
        yield _ToolbarAction("Prompts", "show_prompts")
        yield _ToolbarSep()

        # ── Appearance ──
        yield Label("Appearance: ", classes="_cat-label")
        yield _ToolbarAction("Themes", "open_theme_picker")
        yield _ToolbarAction("Next", "next_theme")
