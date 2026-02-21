## 9. Network Isolation Configuration

**Source:** `toolhive` (`pkg/labels/`, container configs)

ToolHive configures **per-server network isolation** via container labels:

- `network.mode`: `host`, `bridge`, `none`
- `network.allow`: Specific hostnames/IPs the server can reach
- Per-server firewall rules
- DNS isolation

### Relevance to MCP Sentinel
For stdio backends (subprocesses), network isolation could be achieved via:
- Environment variable whitelisting (`HTTP_PROXY`, `NO_PROXY`)
- Systemd socket activation with network namespaces (Linux)
- macOS sandbox profiles

This is niche but relevant for security-sensitive deployments.

**Effort:** High — OS-specific sandboxing.  
**Priority:** P3+ — only for security-hardened deployments.s