"""Custom Textual messages for gateway status updates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.message import Message


class StatusUpdate(Message):
    """Posted when the gateway lifespan emits a status change."""

    def __init__(
        self,
        stage: str,
        status_info: Dict[str, Any],
        is_final: bool = False,
    ) -> None:
        self.stage = stage
        self.status_info = status_info
        self.is_final = is_final
        super().__init__()


class CapabilitiesReady(Message):
    """Posted once capabilities have been discovered and are available."""

    def __init__(
        self,
        tools: List[Any],
        resources: List[Any],
        prompts: List[Any],
        route_map: Optional[Dict[str, tuple]] = None,
    ) -> None:
        self.tools = tools
        self.resources = resources
        self.prompts = prompts
        self.route_map = route_map or {}
        super().__init__()


class ServerStopped(Message):
    """Posted when the uvicorn server thread exits."""

    def __init__(self, error: Optional[str] = None) -> None:
        self.error = error
        super().__init__()
