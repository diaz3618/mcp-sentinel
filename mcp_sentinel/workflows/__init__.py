"""Composite Workflows — DAG-based tool chaining.

Provides YAML-based multi-step tool pipelines with parallelism,
conditionals, retry, and error handling.  Workflows are exposed
as composite MCP tools.
"""

from mcp_sentinel.workflows.dsl import WorkflowDefinition, parse_workflow
from mcp_sentinel.workflows.executor import WorkflowExecutor
from mcp_sentinel.workflows.steps import Step, StepResult, StepStatus

__all__ = [
    "Step",
    "StepResult",
    "StepStatus",
    "WorkflowDefinition",
    "WorkflowExecutor",
    "parse_workflow",
]
