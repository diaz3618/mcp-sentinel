# Composite Tool Workflows

> **Status in analysis table:** "Yes" — MCP Sentinel has no workflow engine.

---

## What It Is

Composite workflows let you define **multi-step tool chains** where the output of one tool feeds into the next. Instead of the LLM manually orchestrating "call tool A, then call tool B with A's result," you define a YAML workflow that the gateway executes as a single tool call.

## How ToolHive Implements It

ToolHive's `pkg/vmcp/composer/` package implements a full DAG (Directed Acyclic Graph) execution engine:

### Workflow Definition (YAML)
```yaml
name: deploy-review
description: "Run tests, lint, and deploy if clean"
steps:
  - id: tests
    tool: ci_server/run_tests
    args:
      branch: "{{ input.branch }}"
  - id: lint
    tool: ci_server/lint
    args:
      branch: "{{ input.branch }}"
  - id: deploy
    tool: deploy_server/deploy
    depends_on: [tests, lint]
    condition: "{{ steps.tests.success && steps.lint.success }}"
    args:
      branch: "{{ input.branch }}"
      test_report: "{{ steps.tests.output }}"
```

### Execution Model
- **Kahn's algorithm** sorts steps into parallel execution levels
- Steps with no dependencies run concurrently via `sync.WaitGroup`
- Each level completes before the next begins
- Template expansion (`{{ }}`) injects previous step outputs into later step args
- Failure modes: `abort` (default), `continue`, or `retry` with configurable attempts

### Elicitation
Steps can pause and request human input via MCP's `elicitation` protocol before proceeding.

## How This Improves MCP Sentinel

Without composite workflows:
- Multi-step operations require the LLM to manually orchestrate each call
- Each round-trip adds latency and uses tokens
- Error handling falls entirely on the LLM
- There's no way to enforce step ordering or dependencies

With composite workflows:
- Complex operations become a single tool call
- The gateway handles parallelism, ordering, and error recovery
- Token usage drops dramatically for multi-step operations
- Operations are reproducible and auditable

## Implementation Path

This is a **P3 feature** (high effort) because it requires:
1. A new `mcp_sentinel/bridge/composer.py` module
2. YAML workflow definition parser
3. DAG topological sort (Python's `graphlib.TopologicalSorter`)
4. Template expansion engine (Jinja2 or simple `str.format_map`)
5. Registering composite workflows as virtual tools in the capability registry
6. Result aggregation and error handling per step

**Estimated effort:** High — this is a significant new subsystem. But `asyncio.gather()` makes parallel execution straightforward in Python.
