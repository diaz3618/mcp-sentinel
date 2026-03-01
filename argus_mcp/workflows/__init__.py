"""Composite Workflows — DAG-based tool chaining.

Provides YAML-based multi-step tool pipelines with parallelism,
conditionals, retry, and error handling.  Workflows are exposed
as composite MCP tools.
"""

from argus_mcp.workflows.dsl import WorkflowDefinition, parse_workflow
from argus_mcp.workflows.executor import WorkflowExecutor
from argus_mcp.workflows.steps import Step, StepResult, StepStatus

__all__ = [
    "Step",
    "StepResult",
    "StepStatus",
    "WorkflowDefinition",
    "WorkflowExecutor",
    "parse_workflow",
]
