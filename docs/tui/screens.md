# TUI Screens Reference

## Screen Architecture

All screens extend a common `BaseScreen` and implement `compose_content()` for
layout. The TUI uses Textual's mode system — each screen is registered as a
mode in `SentinelApp`.

```markdown
SentinelApp
├── DashboardScreen  (mode: "dashboard")
├── ToolsScreen      (mode: "tools")
├── RegistryScreen   (mode: "registry")
└── SettingsScreen   (mode: "settings")
```

## DashboardScreen

**File:** `tui/screens/dashboard.py`
**Key:** `1` or `d`

The primary monitoring screen with a grid layout:

```markdown
┌──────────────────────────────────────────────┐
│  Server Selector (multi-server mode only)    │
├──────────────────┬───────────────────────────┤
│                  │                           │
│  Server Info     │  Backend Status           │
│  - Name          │  - Per-backend state      │
│  - Version       │  - Phase (color-coded)    │
│  - Uptime        │  - Health indicators      │
│  - Transport     │  - Capability counts      │
│                  │                           │
├──────────────────┴───────────────────────────┤
│                                              │
│  Event Log                                   │
│  - Timestamped events                        │
│  - Severity indicators                       │
│  - Backend attribution                       │
│                                              │
├──────────────────────────────────────────────┤
│  Capability Section (tabbed)                 │
│  - Tools | Resources | Prompts               │
│  - Name, backend, description                │
└──────────────────────────────────────────────┘
```

### Widgets Used

| Widget | File | Purpose |
|--------|------|---------|
| `ServerSelectorWidget` | `widgets/server_selector.py` | Multi-server dropdown |
| `ServerInfoWidget` | `widgets/server_info.py` | Server details panel |
| `BackendStatusWidget` | `widgets/backend_status.py` | Backend status grid |
| `EventLogWidget` | `widgets/event_log.py` | Event stream |
| `CapabilitySection` | `widgets/capability_tables.py` | Tabbed capability tables |

## ToolsScreen

**File:** `tui/screens/tools.py`
**Key:** `2`

Full-screen capability explorer with filtering and search.

- Tab switching: `t` (tools), `r` (resources), `p` (prompts)
- Filter toggle for refining results
- Detailed view when selecting a capability
- Tool preview widget for schema inspection

### Widgets Used

| Widget | File | Purpose |
|--------|------|---------|
| `FilterToggleWidget` | `widgets/filter_toggle.py` | Filter controls |
| `ToolPreviewWidget` | `widgets/tool_preview.py` | Tool schema viewer |
| `CapabilitySection` | `widgets/capability_tables.py` | Capability tables |

## RegistryScreen

**File:** `tui/screens/registry.py`
**Key:** `3`

Server browser for discovering and managing MCP servers.

- Registry browser listing available servers
- Server metadata and details panel
- Install panel for adding new backends

### Widgets Used

| Widget | File | Purpose |
|--------|------|---------|
| `RegistryBrowserWidget` | `widgets/registry_browser.py` | Server listing |
| `InstallPanelWidget` | `widgets/install_panel.py` | Backend installation |

## SettingsScreen

**File:** `tui/screens/settings.py`
**Key:** `4` or `s`

Configuration viewer and preferences.

- Current config preview (loaded from server)
- Theme selection
- Application settings

## ToolEditorScreen

**File:** `tui/screens/tool_editor.py`
**Access:** Via Tools screen

Edit and test tool parameters:

- Parameter editor with type-aware input fields
- JSON schema visualization
- Test invocation (dry-run)

### Widgets Used

| Widget | File | Purpose |
|--------|------|---------|
| `ParamEditorWidget` | `widgets/param_editor.py` | Parameter editing |

## SkillsScreen

**File:** `tui/screens/skills.py`
**Access:** Via command palette

Manage installed skill packs:

- List installed skills with enable/disable toggles
- View skill manifests
- Install/uninstall skills

## ElicitationScreen

**File:** `tui/screens/elicitation.py`
**Access:** Triggered by backends

Handle MCP elicitation protocol requests:

- Displays elicitation form from backend
- Captures user input
- Returns response to the requesting backend

### Widgets Used

| Widget | File | Purpose |
|--------|------|---------|
| `ElicitationFormWidget` | `widgets/elicitation_form.py` | Dynamic form |

## ThemeScreen

**File:** `tui/screens/theme_picker.py`
**Key:** `T` (Shift+T)

Visual theme selection:

- Preview of available Textual themes
- Live preview before applying
- Persistent theme preference

## Widget Reference

| Widget | File | Description |
|--------|------|-------------|
| `BackendStatusWidget` | `backend_status.py` | Color-coded backend lifecycle display |
| `CapabilitySection` | `capability_tables.py` | Tabbed tables for tools/resources/prompts |
| `EventLogWidget` | `event_log.py` | Scrollable event timeline |
| `ServerInfoWidget` | `server_info.py` | Server details (name, version, uptime) |
| `ServerSelectorWidget` | `server_selector.py` | Multi-server dropdown with connect action |
| `ToolPreviewWidget` | `tool_preview.py` | Tool JSON schema display |
| `Toolbar` | `toolbar.py` | Action bar |
| `FilterToggleWidget` | `filter_toggle.py` | Capability filter controls |
| `ParamEditorWidget` | `param_editor.py` | Tool parameter editor |
| `InstallPanelWidget` | `install_panel.py` | Backend installation form |
| `RegistryBrowserWidget` | `registry_browser.py` | Server registry browser |
| `ElicitationFormWidget` | `elicitation_form.py` | Dynamic elicitation form |
| `VersionBadgeWidget` | `version_badge.py` | Version display badge |

## Custom Events

| Event | File | Trigger |
|-------|------|---------|
| `CapabilitiesReady` | `events.py` | Backend capabilities loaded |
| `ConnectionLost` | `events.py` | Server connection lost |
| `ConnectionRestored` | `events.py` | Server connection restored |
| `ServerSelected` | `widgets/server_selector.py` | User selects a server |
