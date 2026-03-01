# Example Skills

This directory contains example skills for Argus MCP. Each skill is
a self-contained directory with a `manifest.json` file that defines
tools, workflows, configuration, and dependencies.

## Available Examples

| Skill | Description |
|-------|-------------|
| `code-search` | Search and analyze source code across configured backends |
| `github-integration` | GitHub issue triage and pull request summarization |

## Usage

```bash
# Install a skill into Argus MCP's skill directory
from argus_mcp.skills.manager import SkillManager

manager = SkillManager(skills_dir="skills")
manager.install("examples/skills/code-search")
manager.install("examples/skills/github-integration")

# List installed skills
for skill in manager.list_skills():
    print(f"{skill.name} v{skill.version} [{skill.status.value}]")
```

## Creating Your Own Skill

1. Create a directory with a unique name (lowercase, hyphenated)
2. Add a `manifest.json` following the schema below
3. Install with `SkillManager.install(path)`

### Manifest Schema

See [docs/skills.md](../../docs/skills.md) for the complete reference.

Required fields:

- `name` — Unique skill identifier

Optional fields:

- `version` — Semantic version (default: `"0.0.0"`)
- `description` — Human-readable description
- `author` — Skill author
- `license` — License identifier
- `tools` — List of tool definitions
- `workflows` — List of workflow definitions
- `config` — Default configuration (supports `secret:` prefix)
- `dependencies` — Names of required skills
