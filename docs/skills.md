# Skills System

Skills are portable, self-contained bundles of tools, workflows, and
configuration. They provide a packaging mechanism for distributing
reusable MCP capability sets.

## Skill Structure

A skill is a directory containing a `manifest.json` file:

```markdown
skills/
  my-skill/
    manifest.json
    README.md          # Optional
    templates/         # Optional
```

## Manifest Format

The `manifest.json` file defines the skill's metadata, tools, workflows,
and configuration:

```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "A reusable skill that provides search capabilities",
  "author": "Your Name",
  "license": "MIT",
  "tools": [
    {
      "name": "search_docs",
      "backend": "docs-server",
      "description": "Search documentation files"
    }
  ],
  "workflows": [
    {
      "name": "research",
      "steps": [
        {"tool": "search_docs", "args": {"query": "{{input}}"}}
      ]
    }
  ],
  "config": {
    "api_key": "secret:my-skill-key",
    "max_results": 10
  },
  "dependencies": ["base-tools"]
}
```

### Manifest Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | **yes** | — | Unique skill identifier |
| `version` | string | no | `"0.0.0"` | Semantic version |
| `description` | string | no | `""` | Human-readable description |
| `tools` | list | no | `[]` | Tool definitions |
| `workflows` | list | no | `[]` | Workflow definitions |
| `config` | object | no | `{}` | Default configuration (namespaced) |
| `dependencies` | list | no | `[]` | Names of required skills |
| `author` | string | no | `""` | Skill author |
| `license` | string | no | `""` | License identifier |

## Skill Manager

The `SkillManager` handles the full lifecycle of skills:

### Operations

| Operation | Description |
|-----------|-------------|
| `discover()` | Scan the skills directory, load manifests, respect enabled/disabled state |
| `install(source_path)` | Copy skill into skills directory, validate manifest and dependencies |
| `uninstall(skill_name)` | Remove an installed skill (with path traversal protection) |
| `enable(skill_name)` | Enable a disabled skill |
| `disable(skill_name)` | Disable a skill without removing it |
| `get(skill_name)` | Retrieve an installed skill by name |
| `list_skills()` | List all installed skills |
| `list_enabled()` | List only enabled skills |
| `get_skill_config(name)` | Get namespaced config for a skill |
| `get_all_tools()` | Get tool definitions from all enabled skills |

### State Tracking

Skill enable/disable state is persisted in `skills-state.json` alongside
the skills directory:

```json
{
  "my-skill": "enabled",
  "experimental-tools": "disabled"
}
```

### Security

- **Path traversal protection:** The manager validates that uninstall
  targets are within the skills directory. Attempts to escape the
  skills directory (e.g., `../../etc`) are rejected.
- **Manifest validation:** Invalid manifests (missing `name`, malformed
  JSON) raise `SkillManifestError` and are skipped during discovery.
- **Config namespacing:** Skill configs are isolated by skill name to
  prevent cross-skill configuration conflicts.
- **Secret support:** Config values can reference encrypted secrets via
  the `secret:` prefix (e.g., `"api_key": "secret:my-skill-key"`).

## TUI Integration

Skills can be managed through the **Skills Screen** in the TUI:

- View installed skills with status (enabled/disabled)
- Enable or disable skills
- View skill details and manifest info

Access via the TUI command palette or by navigating to the Skills screen.

## Python API

```python
from mcp_sentinel.skills.manager import SkillManager

manager = SkillManager(skills_dir="skills")

# Discover existing skills
manager.discover()

# Install a new skill
manager.install("/path/to/my-skill")

# List skills
for skill in manager.list_skills():
    print(f"{skill.name} [{skill.status.value}]")

# Enable/disable
manager.disable("experimental-tools")
manager.enable("experimental-tools")

# Get tools from all enabled skills
tools = manager.get_all_tools()
```
