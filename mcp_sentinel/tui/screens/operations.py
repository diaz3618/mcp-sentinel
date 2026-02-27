"""Operations mode — workflows, optimizer, and telemetry.

Houses the heavier operational features (each with Input widgets
or complex layouts) in their own tabs, keeping Dashboard clean.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import TabbedContent, TabPane

from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.widgets.otel_panel import OTelPanel
from mcp_sentinel.tui.widgets.optimizer_panel import OptimizerPanel
from mcp_sentinel.tui.widgets.sync_status import SyncStatusWidget
from mcp_sentinel.tui.widgets.workflows_panel import WorkflowsPanel


class OperationsScreen(SentinelScreen):
    """Operations mode — workflows, tool optimizer, and telemetry."""

    def compose_content(self) -> ComposeResult:
        with TabbedContent(id="ops-tabs"):
            with TabPane("Workflows", id="tab-ops-workflows"):
                yield WorkflowsPanel(id="workflows-panel-widget")
            with TabPane("Optimizer", id="tab-ops-optimizer"):
                yield OptimizerPanel(id="optimizer-panel-widget")
            with TabPane("Telemetry", id="tab-ops-otel"):
                yield OTelPanel(id="otel-panel-widget")
            with TabPane("Sync", id="tab-ops-sync"):
                yield SyncStatusWidget(id="sync-status-widget")
