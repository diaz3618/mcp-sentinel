# GitHub Integration Skill

Triage issues, summarise pull requests, and automate common GitHub
workflows through Argus MCP.

## Tools

| Tool | Backend | Description |
|------|---------|-------------|
| `list_issues` | github | List open issues with filters |
| `get_issue` | github | Retrieve a single issue by number |
| `triage_issue` | github | Classify an issue and suggest labels |
| `list_pull_requests` | github | List open PRs with status |
| `summarise_pr` | github | Summarise a PR diff in plain language |

## Workflows

### issue-triage

Fetch an issue by number, classify it, and add appropriate labels.

```
get_issue ──▶ triage_issue
```

### pr-summary

List open pull requests and summarise the most recent one.
Skips the summary step if no open PRs exist (`condition`).

```
list_pull_requests ──▶ summarise_pr
```

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `github_token` | `${secrets.GITHUB_TOKEN}` | Personal access token (resolved from secrets) |
| `default_repo` | `owner/repo` | Default `owner/repo` to operate on |

## Usage

```python
from argus_mcp.skills.manager import SkillManager

mgr = SkillManager("./examples/skills")
skill = mgr.load("github-integration")
print(skill.manifest.workflows)
```
