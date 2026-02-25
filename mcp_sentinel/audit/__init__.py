"""Audit subsystem — structured event logging for MCP operations.

Public API
----------
- :class:`AuditLogger` — JSON-line file writer with rotation
- :class:`AuditEvent` — Pydantic model for a single audit record
- :class:`AuditSource` / :class:`AuditTarget` / :class:`AuditOutcome` — Sub-models
"""

from mcp_sentinel.audit.logger import AuditLogger
from mcp_sentinel.audit.models import AuditEvent, AuditOutcome, AuditSource, AuditTarget

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuditOutcome",
    "AuditSource",
    "AuditTarget",
]
