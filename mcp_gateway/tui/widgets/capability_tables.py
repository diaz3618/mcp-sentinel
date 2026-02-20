"""Capability DataTable widgets for tools, resources, and prompts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, TabbedContent, TabPane

logger = logging.getLogger(__name__)


def _trunc(text: str | None, max_len: int = 80) -> str:
    """Truncate long descriptions for table display."""
    if not text:
        return "—"
    first_line = text.strip().split("\n")[0]
    if len(first_line) > max_len:
        return first_line[: max_len - 1] + "…"
    return first_line


class CapabilitySection(Widget):
    """Tabbed view of Tools / Resources / Prompts DataTables."""

    tools_count: reactive[int] = reactive(0)
    resources_count: reactive[int] = reactive(0)
    prompts_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        with TabbedContent(id="cap-tabs"):
            with TabPane("Tools (0)", id="tab-tools"):
                yield DataTable(id="dt-tools")
            with TabPane("Resources (0)", id="tab-resources"):
                yield DataTable(id="dt-resources")
            with TabPane("Prompts (0)", id="tab-prompts"):
                yield DataTable(id="dt-prompts")

    def on_mount(self) -> None:
        # Set up columns for each table
        dt_tools = self.query_one("#dt-tools", DataTable)
        dt_tools.add_columns("Name", "Server", "Description")
        dt_tools.cursor_type = "row"
        dt_tools.zebra_stripes = True

        dt_res = self.query_one("#dt-resources", DataTable)
        dt_res.add_columns("Name / URI", "Server", "Description", "MIME Type")
        dt_res.cursor_type = "row"
        dt_res.zebra_stripes = True

        dt_prompts = self.query_one("#dt-prompts", DataTable)
        dt_prompts.add_columns("Name", "Server", "Description", "Arguments")
        dt_prompts.cursor_type = "row"
        dt_prompts.zebra_stripes = True

    # ── Tab label updates ───────────────────────────────────────

    def _update_tab_labels(self) -> None:
        """Re-label tabs with current counts."""
        try:
            tabs = self.query_one("#cap-tabs", TabbedContent)
            tab_pane_tools = tabs.query_one("#tab-tools", TabPane)
            tab_pane_res = tabs.query_one("#tab-resources", TabPane)
            tab_pane_prompts = tabs.query_one("#tab-prompts", TabPane)
            tab_pane_tools.label = f"Tools ({self.tools_count})"  # type: ignore[assignment]
            tab_pane_res.label = f"Resources ({self.resources_count})"  # type: ignore[assignment]
            tab_pane_prompts.label = f"Prompts ({self.prompts_count})"  # type: ignore[assignment]
        except Exception:
            logger.debug("Tab labels not yet available", exc_info=True)

    def watch_tools_count(self) -> None:
        self._update_tab_labels()

    def watch_resources_count(self) -> None:
        self._update_tab_labels()

    def watch_prompts_count(self) -> None:
        self._update_tab_labels()

    # ── Data population ─────────────────────────────────────────

    def populate(
        self,
        tools: List[Any],
        resources: List[Any],
        prompts: List[Any],
        route_map: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> None:
        """Fill all three tables from MCP type lists."""
        rmap = route_map or {}

        # Tools
        dt_tools = self.query_one("#dt-tools", DataTable)
        dt_tools.clear()
        for t in tools:
            server = rmap.get(t.name, ("—", ""))[0]
            dt_tools.add_row(
                t.name,
                server,
                _trunc(t.description),
                key=t.name,
            )
        self.tools_count = len(tools)

        # Resources
        dt_res = self.query_one("#dt-resources", DataTable)
        dt_res.clear()
        for r in resources:
            server = rmap.get(r.name, ("—", ""))[0]
            uri = getattr(r, "uri", r.name)
            mime = getattr(r, "mimeType", None) or "—"
            dt_res.add_row(
                str(uri),
                server,
                _trunc(r.description) if hasattr(r, "description") else "—",
                mime,
                key=r.name,
            )
        self.resources_count = len(resources)

        # Prompts
        dt_prompts = self.query_one("#dt-prompts", DataTable)
        dt_prompts.clear()
        for p in prompts:
            server = rmap.get(p.name, ("—", ""))[0]
            args_list = getattr(p, "arguments", None) or []
            args_str = ", ".join(a.name for a in args_list) if args_list else "—"
            dt_prompts.add_row(
                p.name,
                server,
                _trunc(p.description) if hasattr(p, "description") else "—",
                args_str,
                key=p.name,
            )
        self.prompts_count = len(prompts)
