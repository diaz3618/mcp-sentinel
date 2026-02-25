"""TUI screen definitions for multi-mode navigation."""

from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.screens.dashboard import DashboardScreen
from mcp_sentinel.tui.screens.registry import RegistryScreen
from mcp_sentinel.tui.screens.settings import SettingsScreen
from mcp_sentinel.tui.screens.skills import SkillsScreen
from mcp_sentinel.tui.screens.theme_picker import ThemeScreen
from mcp_sentinel.tui.screens.tools import ToolsScreen

__all__ = [
    "DashboardScreen",
    "RegistryScreen",
    "SentinelScreen",
    "SettingsScreen",
    "SkillsScreen",
    "ThemeScreen",
    "ToolsScreen",
]
