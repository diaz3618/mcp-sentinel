# Code Search Skill

Search and analyse source code across configured MCP backends.

## Tools

| Tool | Backend | Description |
|------|---------|-------------|
| `search_code` | code-index | Full-text search across indexed repositories |
| `find_symbol` | code-index | Find symbol definitions by name |
| `list_files` | code-index | List files matching a glob pattern |

## Workflows

### deep-search

A two-step workflow that searches for code matching a query and then
retrieves symbol context for the top match.

```
search_code ──▶ find_symbol
```

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `max_results` | 50 | Maximum number of search results to return |
| `index_path` | `/var/lib/mcp-sentinel/code-index` | Path to the local code index |

## Usage

```python
from mcp_sentinel.skills.manager import SkillManager

mgr = SkillManager("./examples/skills")
skill = mgr.load("code-search")
print(skill.manifest.tools)
```
