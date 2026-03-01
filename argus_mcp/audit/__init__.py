"""Audit subsystem — structured event logging for MCP operations.

Public API
----------
- :class:`AuditLogger` — JSON-line file writer with rotation
- :class:`AuditEvent` — Pydantic model for a single audit record
- :class:`AuditSource` / :class:`AuditTarget` / :class:`AuditOutcome` — Sub-models
"""

from argus_mcp.audit.logger import AuditLogger
from argus_mcp.audit.models import AuditEvent, AuditOutcome, AuditSource, AuditTarget

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuditOutcome",
    "AuditSource",
    "AuditTarget",
]
