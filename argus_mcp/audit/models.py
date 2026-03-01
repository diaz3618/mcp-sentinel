"""Audit event models — NIST SP 800-53 aligned structured events.

Each audit event captures *who*, *what*, *when*, *where*, *outcome*, and
*duration* for a single MCP operation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditSource(BaseModel):
    """Identity and origin of the request."""

    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_id: Optional[str] = None


class AuditTarget(BaseModel):
    """Destination of the operation."""

    backend: Optional[str] = None
    method: str
    capability_name: str
    original_name: Optional[str] = None


class AuditOutcome(BaseModel):
    """Result metrics."""

    status: str = "success"  # "success" | "error"
    latency_ms: float = 0.0
    error: Optional[str] = None
    error_type: Optional[str] = None


class AuditEvent(BaseModel):
    """A single structured audit event.

    Aligned with NIST SP 800-53 AU-3 (Content of Audit Records):
    - Type of event
    - When the event occurred
    - Where the event occurred
    - Source of the event (identity)
    - Outcome of the event
    """

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str = "mcp_operation"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source: AuditSource = Field(default_factory=AuditSource)
    target: AuditTarget
    outcome: AuditOutcome = Field(default_factory=AuditOutcome)
    metadata: Dict[str, Any] = Field(default_factory=dict)
