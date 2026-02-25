# MCP Sentinel Documentation

> **MCP Sentinel** is a central gateway and management platform for
> [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) servers.
> It aggregates capabilities from multiple backends, provides a REST management
> API, an interactive TUI, and enterprise-grade security features.

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](getting-started.md) | Installation, first run, quick config |
| [Configuration](configuration.md) | Full config reference (YAML / JSON) |
| [CLI Reference](cli/) | Command-line interface |
| [Architecture](architecture/) | System design, component overview, data flow |
| [Management API](api/) | REST endpoints for monitoring and control |
| [Security](security/) | Authentication, authorization, secrets |
| [TUI Guide](tui/) | Interactive terminal UI |
| [Middleware](middleware.md) | Request pipeline and middleware chain |
| [Audit & Observability](audit.md) | Audit logging, telemetry, health checks |
| [Skills](skills.md) | Skill packs — bundled tools and workflows |

## Documentation Map

```markdown
docs/
├── README.md              ← You are here
├── getting-started.md     ← Install & first run
├── configuration.md       ← Full config reference
├── middleware.md           ← Middleware pipeline
├── audit.md               ← Audit logging & observability
├── skills.md              ← Skills system
│
├── architecture/
│   ├── 00-overview.md     ← High-level architecture
│   ├── 01-server.md       ← Server & transport layer
│   ├── 02-bridge.md       ← Bridge: routing, registry, forwarding
│   ├── 03-config.md       ← Config loading pipeline
│   └── 04-runtime.md      ← Service lifecycle
│
├── cli/
│   ├── README.md          ← CLI overview
│   ├── server.md          ← `mcp-sentinel server`
│   ├── tui.md             ← `mcp-sentinel tui`
│   └── secret.md          ← `mcp-sentinel secret`
│
├── security/
│   ├── README.md          ← Security overview
│   ├── authentication.md  ← Incoming auth (JWT, OIDC, local)
│   ├── authorization.md   ← RBAC policies
│   ├── secrets.md         ← Encrypted secret management
│   └── outgoing-auth.md   ← Backend auth (OAuth2, static)
│
├── api/
│   ├── README.md          ← API overview & auth
│   └── endpoints.md       ← Endpoint reference
│
└── tui/
    ├── README.md          ← TUI overview & keybindings
    └── screens.md         ← Screen reference
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Backend** | An MCP server that Sentinel connects to (stdio, SSE, or streamable-http) |
| **Capability** | A tool, resource, or prompt exposed by a backend |
| **Bridge** | Internal layer that connects to backends and aggregates capabilities |
| **Middleware** | Pluggable request pipeline (auth → authz → telemetry → audit → recovery → routing) |
| **Management API** | REST interface at `/manage/v1/` for monitoring and control |
| **TUI** | Textual-based terminal UI that connects to the management API |
| **Optimizer** | Replaces full tool catalog with `find_tool` + `call_tool` meta-tools |
| **Skill** | A portable bundle of tools, workflows, and config |

## Version

Current version: **0.1.0**

License: GPL-3.0-only
