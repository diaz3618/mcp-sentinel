"""Client / TUI configuration models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ClientConfig(BaseModel):
    """TUI / client-side settings.

    Read by the TUI (``argus-mcp tui``) and by ``_dev_launch.py``
    so that server URL, token, theme, and polling behaviour can be
    set in ``config.yaml`` instead of relying on environment variables
    or CLI flags.
    """

    server_url: str = Field(
        default="http://127.0.0.1:9000",
        description="Default Argus server URL the TUI connects to.",
    )
    token: Optional[str] = Field(
        default=None,
        description="Bearer token for the management API.  Supports ${ENV_VAR}.",
    )
    theme: str = Field(
        default="textual-dark",
        description="Default TUI theme (overridden by user preference in settings.json).",
    )
    poll_interval: float = Field(
        default=2.0,
        ge=0.5,
        le=60.0,
        description="Status polling interval in seconds.",
    )
    servers_config: Optional[str] = Field(
        default=None,
        description="Path to servers.json for multi-server mode.",
    )
