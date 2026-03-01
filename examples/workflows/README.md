# Example Workflows

Workflow definitions use a YAML-based DAG format consumed by
`argus_mcp.workflows.dsl.parse_workflow`.  Each YAML file describes
a pipeline of **steps** that reference MCP tools and can express
dependencies, conditions, retry logic, and error strategies.

## Files

| Workflow | Description |
|----------|-------------|
| [data-pipeline.yaml](data-pipeline.yaml) | Fetch → transform → store three-stage ETL |
| [multi-tool-analysis.yaml](multi-tool-analysis.yaml) | Parallel analysis with fan-out / fan-in |

## Schema Quick Reference

```yaml
name: <string>            # Workflow name (required)
description: <string>     # Human-readable description
inputs:                    # Input parameters
  <param>:
    type: <string|number|boolean|object|array>
    description: <string>
steps:
  - id: <string>          # Unique step ID (required)
    tool: <backend.tool>  # Tool to call (required)
    args: {}              # Arguments (supports ${inputs.*} and ${step.output})
    depends_on: []        # Step IDs that must finish first
    condition: <expr>     # Skip step if expression is falsy
    retry: <int>          # Max retries on failure (default: 0)
    on_error: fail|skip|continue
    description: <string>
output: <template>        # Final workflow output template
```

## Loading a Workflow

```python
from argus_mcp.workflows.dsl import load_workflow_yaml

wf = load_workflow_yaml("examples/workflows/data-pipeline.yaml")
for level in wf.topological_order():
    print([s.id for s in level])
```
