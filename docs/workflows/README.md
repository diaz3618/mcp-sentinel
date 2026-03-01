# Composite Workflows

Composite workflows let you chain multiple MCP tools into a single, reusable
pipeline defined in plain YAML.  Each workflow is a **directed acyclic graph
(DAG)** of steps — the engine resolves dependencies automatically, runs
independent steps in parallel, and exposes the whole pipeline as one tool in
`list_tools`.

---

## Why Use Workflows?

| Problem | Workflow Solution |
|---|---|
| Calling 5 tools manually every time you run an analysis | Define the chain once, invoke it with one call |
| Steps that don't depend on each other run sequentially | Independent steps execute in parallel (fan-out) |
| A flaky third-party tool fails occasionally | Built-in `retry` and `on_error` strategies per step |
| Conditional logic ("only run security scan if flag is set") | `condition` expressions on any step |
| Sharing pipelines across a team | Check a `.yaml` file into your repo — done |

---

## Quick Start

### 1. Create a Workflow File

Save a YAML file in the `workflows/` directory (or `examples/workflows/`).

```yaml
# workflows/my-pipeline.yaml
name: my-pipeline
description: Fetch data, transform it, store the result

inputs:
  source_url:
    type: string
    description: URL to fetch raw data from
  format:
    type: string
    description: Target output format (json, csv, parquet)

steps:
  - id: fetch
    tool: http.get
    description: Download raw data
    args:
      url: "${inputs.source_url}"
      timeout: 30

  - id: transform
    tool: transform.convert
    description: Convert to requested format
    depends_on: [fetch]
    args:
      data: "${fetch.output}"
      target_format: "${inputs.format}"
    retry: 2
    on_error: fail

  - id: store
    tool: storage.put
    description: Persist transformed data
    depends_on: [transform]
    args:
      content: "${transform.output}"
      key: "pipeline/${inputs.format}/latest"

output: "${store.output}"
```

### 2. Start Argus MCP

Workflows are automatically discovered at server startup.  The engine scans:

- `workflows/` — primary directory for your own workflow files
- `examples/workflows/` — example / reference workflows shipped with the project

Each valid workflow YAML becomes a **composite tool** — it appears in
`list_tools` alongside regular backend tools.

### 3. Invoke the Workflow

From any MCP client:

```json
{
  "method": "tools/call",
  "params": {
    "name": "my-pipeline",
    "arguments": {
      "source_url": "https://api.example.com/data",
      "format": "json"
    }
  }
}
```

The engine handles the rest: dependency resolution, parallel execution,
interpolation, retries, and final output assembly.

---

## YAML Reference

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | **yes** | Unique workflow name (becomes the tool name) |
| `description` | string | no | Human-readable description |
| `inputs` | object | no | Input parameter schema (JSON-Schema-like) |
| `steps` | list | **yes** | Ordered list of step definitions |
| `output` | string | no | Output template referencing step results |

### Input Parameters

Each key under `inputs` defines a parameter:

```yaml
inputs:
  repo:
    type: string             # JSON Schema type
    description: Repository  # Shown to callers
    required: true           # default: true
```

### Step Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | string | — | **Required.** Unique step identifier |
| `tool` | string | — | **Required.** Backend tool to invoke (`backend.tool_name`) |
| `description` | string | `""` | Human-readable step description |
| `args` | object | `{}` | Arguments passed to the tool (supports interpolation) |
| `depends_on` | list | `[]` | Step IDs that must complete first |
| `condition` | string | `""` | Expression — step is skipped if falsy |
| `retry` | integer | `0` | Max retries on failure (0 = no retry) |
| `on_error` | string | `"fail"` | Error strategy: `fail`, `skip`, or `continue` |

### Output Template

The `output` field is a string with interpolation references.  It determines
what value the composite tool returns to the caller.

```yaml
output: "${transform.output}"
```

If omitted, the engine returns the output of the **last step** in the
definition.

---

## How the DAG Engine Works

### Dependency Resolution

The engine computes a **topological ordering** of steps, grouping them into
**levels**:

```
Level 0:  [code-metrics]   [dependency-audit]    [security-scan]
                 │                  │                   │
                 └──────────────────┼───────────────────┘
                                    │
Level 1:                         [merge]
```

- **Level 0** steps have no `depends_on` — they all run in parallel.
- **Level 1** steps depend on Level 0 — they wait until all dependencies
  complete, then execute.

This is computed via `topological_order()`, which returns
`List[List[Step]]` — a list of levels, each containing the steps that can
run concurrently at that level.

### Parallel Execution (Fan-Out / Fan-In)

Steps within the same level execute concurrently using `asyncio.gather()`:

```
          ┌─── code-metrics ───┐
          │                    │
Input ────┼─── dep-audit ──────┼──── merge ──── Output
          │                    │
          └─── security-scan ──┘
```

This pattern is called **fan-out / fan-in**:  the pipeline fans out to
multiple parallel analyses, then fans in to a single merge step.

### Parameter Interpolation

Step arguments support `${...}` references:

| Pattern | Resolves To |
|---|---|
| `${inputs.param}` | Workflow input parameter value |
| `${step_id.output}` | Output of a completed step |
| `${step_id.status}` | Status string: `completed`, `failed`, `skipped` |

Interpolation happens recursively — an argument can mix literal text with
multiple references:

```yaml
args:
  message: "Results for ${inputs.repo}: ${code-metrics.output}"
```

### Conditional Execution

Add a `condition` to any step.  If the expression evaluates to falsy, the
step is **skipped** (status `SKIPPED`) and subsequent steps see it as
completed.

```yaml
- id: security-scan
  tool: security.scan
  condition: "${inputs.run_security}"
  on_error: skip
```

Supported condition forms:

| Expression | Meaning |
|---|---|
| `${inputs.flag}` | Truthy check on input value |
| `${step.status} == 'completed'` | Equality check |
| `${step.status} != 'failed'` | Inequality check |

### Retry and Error Strategies

Each step can define its own error handling:

| `on_error` | Behavior |
|---|---|
| `fail` | **(default)** Stop the entire workflow immediately |
| `skip` | Mark the step as `SKIPPED` and continue to the next level |
| `continue` | Mark the step as `FAILED` but proceed anyway |

The `retry` field specifies how many times to re-attempt a failed step
before applying the `on_error` strategy:

```yaml
- id: flaky-api
  tool: external.api_call
  retry: 3
  on_error: skip
```

This retries up to 3 times.  If all attempts fail, the step is skipped.

---

## Composite Tools

Every loaded workflow becomes a **composite tool** — it appears in the
`list_tools` response with:

| Field | Value |
|---|---|
| `name` | Workflow `name` field |
| `description` | Workflow `description` (or auto-generated) |
| `inputSchema` | Derived from workflow `inputs` |

When a client calls the composite tool, the engine:

1. Parses the workflow DAG
2. Resolves the topological order
3. Executes levels sequentially, steps within each level in parallel
4. Interpolates arguments between steps
5. Returns the resolved `output` template (or last step's output)

The call goes through the full middleware chain (Recovery → Audit → Routing),
so composite tool invocations are audited and have the same error recovery as
regular tool calls.

---

## TUI Integration

The **Operations → Workflows** tab in the TUI displays all discovered
workflows.  Three actions are available:

| Button | Action |
|---|---|
| **New Workflow** | Opens a YAML editor modal with a starter template.  Validates and saves to the `workflows/` directory. |
| **Run** | Executes the selected workflow as a background task.  Results are shown in a notification. |
| **Delete** | Removes the workflow from the list and deletes its YAML file. |

Select a row in the table to see a step-by-step breakdown of the workflow.

---

## Examples

Two example workflows are included in `examples/workflows/`:

### `data-pipeline.yaml` — Linear ETL

A simple three-stage pipeline: fetch → transform → store.  Demonstrates
sequential dependencies, input substitution, and retry.

```
fetch  →  transform  →  store
```

### `multi-tool-analysis.yaml` — Parallel Fan-Out

Runs three independent analyses in parallel, then merges the results.
Demonstrates parallel execution, conditional skipping, and fan-in.

```
code-metrics     ─┐
dependency-audit ─┼─► merge
security-scan    ─┘
```

---

## Creating Your Own

1. **Copy a template** — start from `examples/workflows/data-pipeline.yaml`
   or use the **New Workflow** button in the TUI.
2. **Define inputs** — declare what parameters callers must provide.
3. **Add steps** — each step needs a unique `id` and a `tool` name matching
   a tool available through your configured backends.
4. **Set dependencies** — use `depends_on` to create the DAG structure.
   Steps without dependencies run in parallel.
5. **Test locally** — use the TUI's Run button for a dry-run, or invoke via
   an MCP client.
6. **Set error handling** — add `retry` and `on_error` to steps that may
   fail transiently.

### Validation

The engine validates every workflow at load time:

- **Required fields** — `name` and `steps` must be present
- **Unique IDs** — no duplicate step IDs
- **Valid references** — every `depends_on` entry must match an existing step ID
- **Acyclicity** — the dependency graph must be a DAG (no cycles)

Invalid workflows are logged as warnings and skipped — they won't appear in
`list_tools`.
