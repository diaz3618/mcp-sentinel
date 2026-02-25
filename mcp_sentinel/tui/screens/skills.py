"""Skills management screen — browse, enable/disable, install skills."""

from __future__ import annotations

import logging
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Label,
    Static,
)

from mcp_sentinel.tui.screens.base import SentinelScreen

logger = logging.getLogger(__name__)


class SkillsScreen(SentinelScreen):
    """TUI screen for managing installed skills.

    Presents a table of installed skills with status, version, and
    description, plus actions to enable/disable/uninstall.
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("e", "toggle_skill", "Enable/Disable"),
        ("u", "uninstall_skill", "Uninstall"),
    ]

    DEFAULT_CSS = """
    SkillsScreen {
        layout: vertical;
    }
    SkillsScreen #skills-container {
        height: 1fr;
    }
    SkillsScreen #detail-panel {
        height: auto;
        max-height: 12;
        border-top: heavy $accent;
        padding: 1 2;
    }
    SkillsScreen #actions-bar {
        height: 3;
        padding: 0 2;
    }
    """

    def __init__(self, skill_manager: Optional[object] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._skills: list[dict[str, str]] = []
        self._selected_skill: str | None = None
        self._skill_manager = skill_manager  # SkillManager instance

    def compose_content(self) -> ComposeResult:
        with Vertical(id="skills-container"):
            yield Label("Skills Management", id="skills-title")
            yield DataTable(id="skills-table")
        with Vertical(id="detail-panel"):
            yield Static("Select a skill to view details.", id="skill-detail")
        with Horizontal(id="actions-bar"):
            yield Button("Enable/Disable", id="btn-toggle", variant="primary")
            yield Button("Uninstall", id="btn-uninstall", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#skills-table", DataTable)
        table.add_columns("Name", "Version", "Status", "Description")
        table.cursor_type = "row"

    def load_skills(self, skills: list[dict[str, str]]) -> None:
        """Populate the table from a list of skill dicts.

        Each dict should have keys: name, version, status, description.
        """
        self._skills = skills
        table = self.query_one("#skills-table", DataTable)
        table.clear()
        for s in skills:
            table.add_row(
                s.get("name", ""),
                s.get("version", ""),
                s.get("status", ""),
                s.get("description", ""),
                key=s.get("name", ""),
            )

    def _refresh_from_manager(self) -> None:
        """Reload skills list from the manager if available."""
        if self._skill_manager is None:
            return
        try:
            from mcp_sentinel.skills.manager import SkillManager

            if isinstance(self._skill_manager, SkillManager):
                skills = []
                for sk in self._skill_manager.list_skills():
                    skills.append(
                        {
                            "name": sk.name,
                            "version": sk.manifest.version,
                            "status": sk.status.value,
                            "description": sk.manifest.description,
                            "author": sk.manifest.author,
                            "license": sk.manifest.license,
                            "dependencies": ", ".join(sk.manifest.dependencies),
                        }
                    )
                self.load_skills(skills)
        except Exception as exc:
            logger.error("Failed to refresh skills from manager: %s", exc)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = str(event.row_key.value) if event.row_key else None
        self._selected_skill = key
        self._update_detail(key)

    def _update_detail(self, skill_name: str | None) -> None:
        detail = self.query_one("#skill-detail", Static)
        if not skill_name:
            detail.update("Select a skill to view details.")
            return

        skill = next((s for s in self._skills if s.get("name") == skill_name), None)
        if not skill:
            detail.update(f"Skill '{skill_name}' not found.")
            return

        lines = [
            f"[b]{skill.get('name', '')}[/b] v{skill.get('version', '')}",
            f"Status: {skill.get('status', '')}",
            f"Author: {skill.get('author', 'N/A')}",
            f"License: {skill.get('license', 'N/A')}",
            "",
            skill.get("description", ""),
        ]
        deps = skill.get("dependencies", "")
        if deps:
            lines.append(f"\nDependencies: {deps}")
        detail.update("\n".join(lines))

    def action_toggle_skill(self) -> None:
        if not self._selected_skill:
            self.notify("No skill selected", severity="warning")
            return

        if self._skill_manager is not None:
            try:
                from mcp_sentinel.skills.manager import SkillManager, SkillStatus

                if isinstance(self._skill_manager, SkillManager):
                    skill = self._skill_manager.get_skill(self._selected_skill)
                    if skill:
                        if skill.status == SkillStatus.ENABLED:
                            self._skill_manager.disable(self._selected_skill)
                            self.notify(f"Disabled '{self._selected_skill}'")
                        else:
                            self._skill_manager.enable(self._selected_skill)
                            self.notify(f"Enabled '{self._selected_skill}'")
                        self._refresh_from_manager()
                        return
            except Exception as exc:
                self.notify(f"Error toggling skill: {exc}", severity="error")
                return

        self.notify(
            f"Toggle '{self._selected_skill}' requested (no manager connected)",
            severity="information",
        )

    def action_uninstall_skill(self) -> None:
        if not self._selected_skill:
            self.notify("No skill selected", severity="warning")
            return

        if self._skill_manager is not None:
            try:
                from mcp_sentinel.skills.manager import SkillManager

                if isinstance(self._skill_manager, SkillManager):
                    self._skill_manager.uninstall(self._selected_skill)
                    self.notify(f"Uninstalled '{self._selected_skill}'")
                    self._selected_skill = None
                    self._refresh_from_manager()
                    return
            except Exception as exc:
                self.notify(f"Error uninstalling skill: {exc}", severity="error")
                return

        self.notify(
            f"Uninstall '{self._selected_skill}' requested (no manager connected)",
            severity="warning",
        )

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle":
            self.action_toggle_skill()
        elif event.button.id == "btn-uninstall":
            self.action_uninstall_skill()
