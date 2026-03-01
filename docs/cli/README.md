# CLI Reference

Argus MCP provides three subcommands:

| Command | Description |
|---------|-------------|
| [`argus-mcp server`](server.md) | Run the headless gateway server |
| [`argus-mcp tui`](tui.md) | Launch the interactive terminal UI |
| [`argus-mcp secret`](secret.md) | Manage encrypted secrets |

## Usage

```
argus-mcp [-h] {server,tui,secret} ...
```

## Global Help

```bash
argus-mcp --help
argus-mcp server --help
argus-mcp tui --help
argus-mcp secret --help
```

## Entry Point

The CLI is installed as the `argus-mcp` console script (defined in
`pyproject.toml`). It can also be invoked as a Python module:

```bash
python -m argus_mcp server
```
