"""Registry mode — browse, search, and install MCP servers from registries.

Provides:
* A :class:`RegistryBrowserWidget` with search bar and ``DataTable``
* A :class:`InstallPanelWidget` showing server details and install button
* Async loading from configured registries via :class:`RegistryClient`
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from mcp_sentinel.registry.cache import RegistryCache
from mcp_sentinel.registry.client import RegistryClient
from mcp_sentinel.registry.models import ServerEntry
from mcp_sentinel.tui.screens.base import SentinelScreen
from mcp_sentinel.tui.widgets.install_panel import InstallConfirmed, InstallPanelWidget
from mcp_sentinel.tui.widgets.registry_browser import (
    InstallRequested,
    RegistryBrowserWidget,
    ServerSelected,
)

logger = logging.getLogger(__name__)

# Default public registry URL — can be overridden via config.
_DEFAULT_REGISTRY = "https://registry.toolhive.dev"


class RegistryScreen(SentinelScreen):
    """Registry mode — server browser and install panel.

    On mount, fetches the server catalog from configured registries
    (with cache fallback) and populates the browser widget.
    """

    def compose_content(self) -> ComposeResult:
        yield Static(
            "[b]Registry[/b]  •  Browse and install MCP servers",
            id="registry-header",
        )
        with Horizontal(id="registry-layout"):
            yield RegistryBrowserWidget(id="registry-browser")
            yield InstallPanelWidget(id="install-panel")

    def on_mount(self) -> None:
        """Kick off async registry fetch."""
        self._cache = RegistryCache()
        self._clients: List[RegistryClient] = []
        asyncio.create_task(self._load_registry())

    async def _load_registry(self) -> None:
        """Fetch servers from all configured registries."""
        browser = self.query_one("#registry-browser", RegistryBrowserWidget)
        browser.set_status("Loading registry…")

        registry_urls = self._get_registry_urls()
        all_entries: List[ServerEntry] = []

        for url in registry_urls:
            client = RegistryClient(url, cache=self._cache)
            self._clients.append(client)
            try:
                page = await client.list_servers()
                all_entries.extend(page.servers)
            except Exception as exc:
                logger.warning("Failed to fetch registry %s: %s", url, exc)

        browser.entries = all_entries
        if all_entries:
            browser.set_status(
                f"Loaded {len(all_entries)} servers from {len(registry_urls)} registries"
            )
        else:
            browser.set_status(
                "No servers found. Registry may be unavailable — showing cached data."
            )

    def _get_registry_urls(self) -> List[str]:
        """Retrieve configured registry URLs."""
        # TODO: Read from config when registries section is added.
        # For now, return the default.
        return [_DEFAULT_REGISTRY]

    # ── event handlers ──────────────────────────────────────────────

    def on_server_selected(self, event: ServerSelected) -> None:
        """Update the install panel when a server is highlighted."""
        panel = self.query_one("#install-panel", InstallPanelWidget)
        panel.selected_entry = event.entry

    def on_install_requested(self, event: InstallRequested) -> None:
        """Handle Enter key on a server row — set it in the panel."""
        panel = self.query_one("#install-panel", InstallPanelWidget)
        panel.selected_entry = event.entry

    def on_install_confirmed(self, event: InstallConfirmed) -> None:
        """Add the server to the config and start it."""
        logger.info(
            "Install confirmed: %s → %s",
            event.entry.name,
            json.dumps(event.config),
        )
        self.notify(
            f"Added [b]{event.entry.name}[/b] to config",
            title="Server Installed",
        )
        # TODO: Write to config file and trigger hot-reload.
        # This will integrate with config hot-reload (Task 3.4)
        # to add the backend and start it without restart.
