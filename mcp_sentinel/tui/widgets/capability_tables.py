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


def _attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    """Get a value from *obj* whether it is a dict or an object with attrs.

    This lets ``populate()`` work with both MCP SDK objects
    (in-process mode) and plain dicts returned by the management API.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


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
        """Re-label tabs with current counts.

        Uses ``TabbedContent.get_tab()`` to obtain the actual ``Tab``
        widget (the clickable button) rather than setting
        ``TabPane.label`` which does not propagate to the visible tab.
        """
        try:
            tabs = self.query_one("#cap-tabs", TabbedContent)
            tabs.get_tab("tab-tools").label = f"Tools ({self.tools_count})"
            tabs.get_tab("tab-resources").label = f"Resources ({self.resources_count})"
            tabs.get_tab("tab-prompts").label = f"Prompts ({self.prompts_count})"
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
        """Fill all three tables from MCP type lists or API dicts.

        Items may be either MCP SDK objects (with ``.name``, ``.description``
        attributes) or plain dicts returned by the management API.
        """
        rmap = route_map or {}

        # Tools
        dt_tools = self.query_one("#dt-tools", DataTable)
        dt_tools.clear()
        for t in tools:
            name = _attr_or_key(t, "name", "—")
            server = rmap.get(name, ("—", ""))[0]
            desc = _attr_or_key(t, "description")
            dt_tools.add_row(
                name,
                server,
                _trunc(desc),
                key=name,
            )
        self.tools_count = len(tools)

        # Resources
        dt_res = self.query_one("#dt-resources", DataTable)
        dt_res.clear()
        for r in resources:
            name = _attr_or_key(r, "name", "—")
            server = rmap.get(name, ("—", ""))[0]
            uri = _attr_or_key(r, "uri", name)
            mime = _attr_or_key(r, "mimeType") or _attr_or_key(r, "mime_type") or "—"
            desc = _attr_or_key(r, "description")
            dt_res.add_row(
                str(uri),
                server,
                _trunc(desc) if desc else "—",
                mime,
                key=name,
            )
        self.resources_count = len(resources)

        # Prompts
        dt_prompts = self.query_one("#dt-prompts", DataTable)
        dt_prompts.clear()
        for p in prompts:
            name = _attr_or_key(p, "name", "—")
            server = rmap.get(name, ("—", ""))[0]
            desc = _attr_or_key(p, "description")
            args_raw = _attr_or_key(p, "arguments") or []
            if args_raw:
                # Handle both objects with .name and dicts with "name"
                arg_names = [_attr_or_key(a, "name", str(a)) for a in args_raw]
                args_str = ", ".join(arg_names)
            else:
                args_str = "—"
            dt_prompts.add_row(
                name,
                server,
                _trunc(desc) if desc else "—",
                args_str,
                key=name,
            )
        self.prompts_count = len(prompts)
