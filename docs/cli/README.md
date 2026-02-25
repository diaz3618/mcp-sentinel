# CLI Reference

MCP Sentinel provides three subcommands:

| Command | Description |
|---------|-------------|
| [`mcp-sentinel server`](server.md) | Run the headless gateway server |
| [`mcp-sentinel tui`](tui.md) | Launch the interactive terminal UI |
| [`mcp-sentinel secret`](secret.md) | Manage encrypted secrets |

## Usage

```markdown
mcp-sentinel [-h] {server,tui,secret} ...
```

## Global Help

```bash
mcp-sentinel --help
mcp-sentinel server --help
mcp-sentinel tui --help
mcp-sentinel secret --help
```

## Entry Point

The CLI is installed as the `mcp-sentinel` console script (defined in
`pyproject.toml`). It can also be invoked as a Python module:

```bash
python -m mcp_sentinel server
```
