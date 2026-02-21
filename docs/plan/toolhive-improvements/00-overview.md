# ToolHive Improvements Plan — Index

> Comprehensive development plan for MCP Sentinel based on deep analysis of the ToolHive ecosystem.  
> Generated from inspection of 4 repositories: `toolhive`, `toolhive-cloud-ui`, `toolhive-registry-server`, `toolhive-studio`.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Development Roadmap](development-roadmap.md) | Phased implementation plan (32 features across 5 phases) |
| [TUI Layout Analysis](tui-layout-analysis.md) | How to scale the TUI with Modes, TabbedContent, Modals, Command Palette |
| [Additional Features](additional-features.md) | 15 features found in repos not in the original analysis |

---

## Explanation Documents

Detailed write-ups for each feature from the [comparison table](../toolhive-analysis.md). Each explains **what it is, how ToolHive does it, how it improves MCP Sentinel, and the implementation path**.

### Features Marked "Yes" (Gaps to Fill)

| # | Feature | Priority | Effort | Doc |
|---|---------|----------|--------|-----|
| 01 | Streamable HTTP Transport | P3 | Low | [explanation/01-streamable-http-transport.md](explanation/01-streamable-http-transport.md) |
| 02 | Conflict Resolution Strategies | P0 | Low | [explanation/02-conflict-resolution.md](explanation/02-conflict-resolution.md) |
| 03 | Tool Filtering (Allow/Deny) | P0 | Low | [explanation/03-tool-filtering.md](explanation/03-tool-filtering.md) |
| 04 | Tool Renaming / Description Override | P1 | Low | [explanation/04-tool-renaming.md](explanation/04-tool-renaming.md) |
| 05 | Composite Tool Workflows | P3 | High | [explanation/05-composite-workflows.md](explanation/05-composite-workflows.md) |
| 06 | Optimizer (find_tool / call_tool) | P2 | Medium | [explanation/06-optimizer.md](explanation/06-optimizer.md) |
| 15 | Health Checks & Circuit Breaker | P1 | Medium | [explanation/15-health-checks.md](explanation/15-health-checks.md) |
| 16 | Middleware Chain Architecture | P1 | Medium | [explanation/16-middleware-chain.md](explanation/16-middleware-chain.md) |
| 17 | Backend Status Model | P2 | Medium | [explanation/17-backend-status-model.md](explanation/17-backend-status-model.md) |
| 18 | Secret Management | P0-P3 | Low-Med | [explanation/18-secret-management.md](explanation/18-secret-management.md) |
| 19 | Session Management | P2 | Med-High | [explanation/19-session-management.md](explanation/19-session-management.md) |
| 20 | Config Format & Validation | P0-P1 | Low | [explanation/20-config-format.md](explanation/20-config-format.md) |

### Features Marked "Explain" (Need Explanation)

| # | Feature | Priority | Effort | Doc |
|---|---------|----------|--------|-----|
| 07 | Incoming Authentication (JWT/OIDC) | P3 | High | [explanation/07-incoming-auth.md](explanation/07-incoming-auth.md) |
| 08 | Outgoing Authentication (Backend Creds) | P2-P3 | Low-High | [explanation/08-outgoing-auth.md](explanation/08-outgoing-auth.md) |
| 09 | Authorization (Policy-Based Access) | P3 | Med-High | [explanation/09-authorization.md](explanation/09-authorization.md) |
| 10 | Audit Logging (Structured Events) | P1 | Medium | [explanation/10-audit-logging.md](explanation/10-audit-logging.md) |
| 11 | OpenTelemetry Integration | P3 | High | [explanation/11-opentelemetry.md](explanation/11-opentelemetry.md) |
| 12 | Server Groups | P2 | Low | [explanation/12-server-groups.md](explanation/12-server-groups.md) |
| 13 | MCP Server Registry | P2 | Medium | [explanation/13-registry.md](explanation/13-registry.md) |
| 14 | Client Auto-Configuration | P2 | Low | [explanation/14-client-auto-config.md](explanation/14-client-auto-config.md) |

---

## Methodology

All analysis was produced by **inspecting actual source code** in the ToolHive repos, not by guessing or assuming. For each feature:

1. **Located the implementation** in the relevant ToolHive repo
2. **Read the source code** to understand the architecture and design patterns
3. **Mapped to MCP Sentinel** with concrete file paths and code examples
4. **Estimated effort** based on the Python/Textual implementation requirements

### Repos Inspected

| Repo | Language | Lines Analyzed | Key Insights |
|------|----------|---------------|--------------|
| `toolhive` | Go | ~50,000+ | vmcp aggregator, middleware chain, optimizer, composer, health monitor, auth, audit, telemetry |
| `toolhive-cloud-ui` | TypeScript/Next.js | ~30,000+ | Server catalog, AI chat playground, MCP transports, tool selector |
| `toolhive-registry-server` | Go | ~15,000+ | Registry API v0.1, 5 data sources, sync coordinator, skills system |
| `toolhive-studio` | TypeScript/Electron | ~40,000+ | Server lifecycle, polling engine, feature flags, 7 AI providers, tool customization, secrets |

### TUI Research Sources

| Source | Type | Key Pattern |
|--------|------|-------------|
| Textual framework | Python TUI library | Modes, TabbedContent, ModalScreen, Command Palette |
| Bagels | Financial TUI (Textual) | Tab-driven page composition |
| Dolphie | MySQL monitor (Textual) | Panel toggle system |
| Crush | Chat TUI (Bubble Tea) | Dialog overlay stack |
| amux | Terminal mux (Bubble Tea) | Three-pane layout |

---

## Summary Statistics

- **20 explanation documents** covering every feature in the comparison table
- **15 additional features** discovered beyond the original analysis
- **32 implementation items** in the development roadmap
- **5 phases** from quick wins to ecosystem integration
- **~8-10 weeks** estimated timeline with parallel execution
- **4 TUI modes** recommended for scaling the interface
