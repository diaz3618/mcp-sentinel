"""Workflow step definitions and results.

Each step represents a single unit of work in a workflow DAG.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Execution status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of executing a single workflow step."""

    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class Step:
    """A single step in a workflow DAG.

    Attributes
    ----------
    id:
        Unique step identifier within the workflow.
    tool:
        Tool name to invoke (e.g. ``backend.tool_name``).
    args:
        Arguments to pass to the tool (supports ``${step_id.output}`` refs).
    depends_on:
        List of step IDs that must complete before this step runs.
    condition:
        Optional expression to evaluate — step is skipped if falsy.
        Supports simple checks like ``${step_id.status} == 'completed'``.
    retry:
        Max retry count on failure (0 = no retry).
    on_error:
        Error strategy: ``fail`` (default), ``skip``, ``continue``.
    description:
        Human-readable description.
    """

    id: str
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    condition: str = ""
    retry: int = 0
    on_error: str = "fail"
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Step:
        """Parse from a config/YAML dict."""
        return cls(
            id=data["id"],
            tool=data.get("tool", ""),
            args=data.get("args", {}),
            depends_on=data.get("depends_on", []),
            condition=data.get("condition", ""),
            retry=data.get("retry", 0),
            on_error=data.get("on_error", "fail"),
            description=data.get("description", ""),
        )
