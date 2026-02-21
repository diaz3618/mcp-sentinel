# TUI Layout Analysis — Scaling MCP Sentinel's Interface

> Research-based analysis of TUI layout patterns for adding features without overloading the UI.  
> Sources: Textual framework docs, Bagels, Dolphie, amux, Crush, ToolHive Studio navigation.

---

## Table of Contents

1. [Current TUI Layout](#current-tui-layout)
2. [The Scaling Problem](#the-scaling-problem)
3. [Layout Patterns Analyzed](#layout-patterns-analyzed)
4. [Recommended Architecture](#recommended-architecture)
5. [Screen-by-Screen Breakdown](#screen-by-screen-breakdown)
6. [Navigation Design](#navigation-design)
7. [Command Palette Integration](#command-palette-integration)
8. [Reference TUI Applications](#reference-tui-applications)
9. [Per-Feature Layout Examples](#per-feature-layout-examples)

---

## Current TUI Layout

MCP Sentinel currently uses a **single-screen layout**:

```
┌─── Header ───────────────────────────────────────────────┐
├─── Toolbar (categorized action buttons) ─────────────────┤
│                                                          │
│  ┌─── ServerInfo ──────┐  ┌─── EventLog ───────────────┐ │
│  │ Server details      │  │ Real-time event stream     │ │
│  ├─── BackendStatus ───┤  │                            │ │
│  │ Backend list        │  │                            │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌─── CapabilitySection ───────────────────────────────┐ │
│  │ Tools / Resources / Prompts tables                  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
├─── Footer (keybindings) ─────────────────────────────────┤
└──────────────────────────────────────────────────────────┘
```

This works for the current feature set (~5 widgets). But adding health checks, server groups, tool customization, audit logs, settings, and a registry browser would overwhelm a single screen.

---

## The Scaling Problem

Features planned for MCP Sentinel need **dedicated UI space**:

| Feature | UI Needs |
|---------|----------|
| Health monitoring | Health status per backend, condition history, circuit breaker state |
| Server groups | Collapsible group tree, group-level actions |
| Tool customization | Per-tool enable/disable, description editing, diff view |
| Audit log viewer | Searchable/filterable structured log stream |
| Registry browser | Server catalog, search, detail/tools tabs, add-to-config |
| Settings | Config editor, timeout tuning, feature flags |
| Client auto-config | Template selection, preview, copy/write actions |
| AI chat playground | Message stream, model selector, server/tool picker |

**Fitting all of this into a single screen is impossible.** The TUI needs a multi-screen architecture.

---

## Layout Patterns Analyzed

### Pattern 1: Textual Modes (Independent Screen Stacks)

**How it works:** Each `Mode` has its own independent screen stack. Switching modes completely swaps the visible content, similar to virtual desktops.

```python
class SentinelApp(App):
    MODES = {
        "dashboard": DashboardScreen,
        "tools": ToolsScreen,
        "registry": RegistryScreen,
        "settings": SettingsScreen,
    }
```

**Pros:**

- Complete screen isolation — each mode is its own world
- No layout conflicts between features
- Natural keyboard navigation (`1`, `2`, `3`, `4` for modes)
- Modes can be popped/pushed independently

**Cons:**

- Switching modes loses scroll position
- No persistent sidebar across modes
- Requires careful state management (each mode needs its own data loading)

**Used by:** Textual framework's built-in design pattern.

---

### Pattern 2: TabbedContent (Sub-navigation within a screen)

**How it works:** Textual's `TabbedContent` widget provides tab-based switching within a single screen. Good for related content that shares context.

```python
with TabbedContent():
    with TabPane("Overview"):
        yield ServerInfoWidget()
    with TabPane("Tools"):
        yield ToolsTable()
    with TabPane("Health"):
        yield HealthPanel()
```

**Pros:**

- Lightweight switching, no full screen replacement
- Shared context (sidebar, header visible alongside tabs)
- Familiar tab metaphor
- Good for related data views

**Cons:**

- Limited to sub-navigation (too many tabs causes overflow)
- All tab content loads even when hidden (unless lazy-loaded)

**Used by:** Bagels (page tabs), ToolHive Cloud UI (server detail tabs).

---

### Pattern 3: ModalScreen (Dialog Overlays)

**How it works:** Push a modal screen on top of the current screen. Used for focused tasks that temporarily interrupt the main workflow.

```python
class ConfirmDialog(ModalScreen[bool]):
    def compose(self):
        yield Grid(
            Label("Are you sure?"),
            Button("Yes", id="yes"),
            Button("No", id="no"),
        )
```

**Pros:**

- Doesn't disrupt main screen state
- Natural for confirmations, forms, detail views
- Can return values to the calling screen
- Focuses user attention

**Cons:**

- Not suitable for persistent views
- Stacking multiple modals is confusing
- Limited to focused, short-lived tasks

**Used by:** Crush (19+ dialog types), ToolHive Studio (confirmations).

---

### Pattern 4: Sidebar Toggle (Panel Visibility)

**How it works:** A persistent sidebar that can be shown/hidden via keybinding. Contains navigation, server groups, or context info.

```python
class SidebarPanel(Widget):
    def compose(self):
        yield Tree("Servers", data=self.server_tree)

# Toggle with keybinding
def action_toggle_sidebar(self):
    self.query_one(SidebarPanel).toggle_class("hidden")
```

**Pros:**

- Persistent navigation always available
- Toggle via keybinding keeps screen clean when not needed
- Good for server groups / tree navigation
- Can animate slide-in/slide-out

**Cons:**

- Takes horizontal space from main content
- Only works for narrow, navigational content
- Needs responsive handling for small terminals

**Used by:** Dolphie (panel toggles), ToolHive Studio (server groups sidebar).

---

### Pattern 5: ContentSwitcher (View Mode Toggle)

**How it works:** Swap between different widget layouts for the same data. E.g., compact vs. expanded backend view.

```python
with ContentSwitcher(initial="compact"):
    yield CompactBackendList(id="compact")
    yield ExpandedBackendView(id="expanded")

def action_toggle_view(self):
    switcher = self.query_one(ContentSwitcher)
    switcher.current = "expanded" if switcher.current == "compact" else "compact"
```

**Pros:**

- Same data, different presentation
- Smooth transition between views
- User preference for information density

**Cons:**

- Only useful for alternative views of identical data
- Both views need to stay in sync

**Used by:** ToolHive Cloud UI (grid/list toggle).

---

### Pattern 6: Command Palette (Power User Navigation)

**How it works:** Textual has a built-in Command Palette (`ctrl+p`) with fuzzy search. Register commands via a `Provider` class.

```python
class SentinelCommandProvider(Provider):
    async def search(self, query: str):
        for cmd in self.commands:
            if query.lower() in cmd.name.lower():
                yield Hit(score, cmd.name, cmd.callback)
```

**Pros:**

- Keyboard-driven navigation for power users
- Every action is discoverable via search
- No screen real estate required
- Textual provides the infrastructure for free

**Cons:**

- Not discoverable for new users (need to know `ctrl+p`)
- Not suitable as primary navigation (supplement only)

**Used by:** VS Code, Textual framework built-in.

---

## Recommended Architecture

**Hybrid pattern: Modes + TabbedContent + ModalScreen + Command Palette**

This is the combination that scales best based on the analyzed patterns:

```
┌─── Header ───────────────────────────────────────────────┐
├─── Mode Bar: [Dashboard] [Tools] [Registry] [Settings] ──┤
│                                                          │
│  ┌────────── Mode-specific content ───────────────────┐  │
│  │                                                    │  │
│  │  (Each mode has its own full-screen layout)        │  │
│  │                                                    │  │
│  │  ┌── TabbedContent (sub-navigation) ────────────┐  │  │
│  │  │  [Tab A]  [Tab B]  [Tab C]                   │  │  │
│  │  │  ┌─── Tab content ────────────────────────┐  │  │  │
│  │  │  │                                        │  │  │  │
│  │  │  └────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
├─── Footer (keybindings + mode indicators) ───────────────┤
└──────────────────────────────────────────────────────────┘

  + ModalScreen overlays for: confirmations, detail views,
    export dialogs, secrets editor
    
  + Command Palette (ctrl+p) for: quick navigation,
    all actions searchable
```

### Architecture Details

| Layer | Pattern | Purpose |
|-------|---------|---------|
| **Top-level** | Modes (4-5) | Major feature areas |
| **Sub-level** | TabbedContent | Related views within a mode |
| **Overlays** | ModalScreen | Focused tasks, confirmations, forms |
| **Navigation** | Command Palette | Power user shortcut to any action |
| **View control** | ContentSwitcher | Compact/expanded toggles where relevant |
| **Optional** | Sidebar | Server groups tree (toggle-able) |

---

## Screen-by-Screen Breakdown

### Mode 1: Dashboard (Default)

The current main screen, refined:

```
┌─── Dashboard ────────────────────────────────────────────┐
│                                                          │
│  ┌─── Server Info ─────┐  ┌─── Event Log ─────────────┐  │
│  │ Endpoint, status    │  │ Real-time event stream    │  │
│  │ Tool/resource count │  │ Filterable by type        │  │
│  ├─── Backend Health ──┤  │                           │  │
│  │ ● server-a [Ready]  │  │ 10:30 tool_call github..  │  │
│  │ ● server-b [Degraded│  │ 10:29 connect  db-server  │  │
│  │ ✕ server-c [Failed] │  │ 10:28 error    search..   │  │
│  └─────────────────────┘  └───────────────────────────┘  │
│                                                          │
│  ┌─── Aggregate Stats ─────────────────────────────────┐ │
│  │ 3 backends │ 2 healthy │ 1 failed │ 42 tools │ ...  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

### Mode 2: Tools & Capabilities

Full tool catalog with customization:

```
┌─── Tools ──────────────────────────────────────────────────┐
│                                                            │
│  [All Tools]  [By Server]  [Customized]                    │
│                                                            │
│  Search: [________________]                                │
│                                                            │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Tool Name         Server      Enabled  Description.    ││
│  │ ────────────────────────────────────────────────────── ││
│  │ search_issues     github      [✓]      Search GitHub.. ││
│  │ create_pr         github      [✓]      Create a pull.. ││
│  │ query_db          database    [✓]      Execute SQL..   ││
│  │ drop_table        database    [ ]      ⚠ Disabled      ││
│  │ ...                                                    ││
│  └────────────────────────────────────────────────────────┘│
│                                                            │
│  [Enter] Details  [Space] Toggle  [E] Edit Description     │
└────────────────────────────────────────────────────────────┘
```

---

### Mode 3: Registry

Browse and add servers from connected registries:

```
┌─── Registry ──────────────────────────────────────────────┐
│                                                           │
│  Registry: [toolhive-official ▼]  Search: [__________]    │
│                                                           │
│  ┌───────────────────────────────────────────────────────┐│
│  │ Name              Transport  Tools  Version  Status   ││
│  │ ────────────────────────────────────────────────────  ││
│  │ github-mcp        SSE        12     v2.1.0   ✓ Added  ││
│  │ postgres-mcp      stdio      8      v1.3.0            ││
│  │ slack-mcp         HTTP       15     v3.0.0            ││
│  │ filesystem-mcp    stdio      6      v1.0.0   ✓ Added  ││
│  └───────────────────────────────────────────────────────┘│
│                                                           │
│  [Enter] View Details  [A] Add to Config  [/] Search      │
└───────────────────────────────────────────────────────────┘
```

---

### Mode 4: Settings

Configuration and preferences:

```
┌─── Settings ─────────────────────────────────────────────┐
│                                                          │
│  [General]  [Timeouts]  [Features]  [Logs]  [About]      │
│                                                          │
│  ┌─── General ──────────────────────────────────────────┐│
│  │                                                      ││
│  │ Conflict Resolution:  [prefix ▼]                     ││
│  │ Prefix Separator:     [______]                       ││
│  │ Config Format:        ○ JSON  ● YAML                 ││
│  │                                                      ││
│  │ ── Feature Flags ──                                  ││
│  │ Health checks:        [✓]                            ││
│  │ Audit logging:        [✓]                            ││
│  │ Optimizer:            [ ]                            ││
│  │ Composite workflows:  [ ]  (experimental)            ││
│  │                                                      ││
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  [S] Save  [R] Reset  [X] Export Config                  │
└──────────────────────────────────────────────────────────┘
```

---

### Modal Overlays

| Modal | Trigger | Content |
|-------|---------|---------|
| Server Detail | `Enter` on a backend | Full server info, tools list, health history, actions |
| Tool Detail | `Enter` on a tool | Full tool schema, input/output types, description |
| Confirm Dialog | Destructive actions | "Are you sure?" with reason |
| Export Config | `X` from settings | Client selector, config preview, copy/write |
| Secrets Editor | From settings | Add/edit/delete secrets (names only) |
| Error Detail | `Enter` on an error | Full stack trace, context, suggestions |

---

## Navigation Design

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Switch to Dashboard mode |
| `2` | Switch to Tools mode |
| `3` | Switch to Registry mode |
| `4` | Switch to Settings mode |
| `ctrl+p` | Open Command Palette |
| `Tab` | Cycle between widgets in current mode |
| `/` | Focus search (when available) |
| `?` | Show keybinding help |
| `q` | Quit |

### Command Palette Actions

All actions accessible via `ctrl+p`:

- "Switch to Dashboard"
- "Switch to Tools"
- "Show server: github-server"
- "Show tool: search_issues"
- "Toggle health checks"
- "Export config for Cursor"
- "Open audit log"
- "Change theme"
- "Restart backend: database-server"

---

## Command Palette Integration

```python
from textual.command import Provider, Hit

class SentinelCommandProvider(Provider):
    """Provide all MCP Sentinel actions to the command palette."""
    
    async def search(self, query: str) -> AsyncIterator[Hit]:
        # Mode switching
        for mode_name, mode_label in [
            ("dashboard", "Dashboard"),
            ("tools", "Tools & Capabilities"),
            ("registry", "Registry Browser"),
            ("settings", "Settings"),
        ]:
            if query.lower() in mode_label.lower():
                yield Hit(
                    score=80,
                    match_display=f"Switch to {mode_label}",
                    command=partial(self.app.switch_mode, mode_name),
                )
        
        # Tool search
        for tool in self.app.all_tools:
            if query.lower() in tool.name.lower():
                yield Hit(
                    score=60,
                    match_display=f"Show tool: {tool.name}",
                    command=partial(self.app.show_tool_detail, tool.name),
                )
        
        # Backend actions
        for backend in self.app.backends:
            if query.lower() in backend.name.lower():
                yield Hit(
                    score=70,
                    match_display=f"Show server: {backend.name}",
                    command=partial(self.app.show_server_detail, backend.name),
                )
```

---

## Reference TUI Applications

### Bagels (Python/Textual) — Financial TUI

- **Pattern:** Tab bar at top switches entire page content
- **Strength:** Clean separation between Journal, Accounts, Reports pages
- **Relevant:** Their `module_compose()` pattern for pluggable page widgets
- **Repo:** Open source, Textual-based

### Dolphie (Python/Textual) — MySQL Monitor

- **Pattern:** `TabManager` for multiple database connections + 12 toggleable panels
- **Strength:** `batch_update()` for efficient multi-panel refresh
- **Relevant:** Their panel toggle approach (keybinding shows/hides data panels)
- **Repo:** Open source, Textual-based

### Crush (Go/Bubble Tea) — Chat TUI

- **Pattern:** Chat-centric main view + dialog overlay stack (19+ dialog types)
- **Strength:** Clean modal dialog system for confirmations, settings, details
- **Relevant:** Dialog overlay architecture for non-disruptive focused tasks

### amux (Go/Bubble Tea) — Terminal Multiplexer

- **Pattern:** Three-pane layout manager + compositor
- **Strength:** Terminal PTY embedding within TUI panels
- **Relevant:** Multi-pane layout with configurable splits (less applicable to MCP Sentinel)

### Key Takeaways from Reference Apps

1. **Tab/Mode navigation** is the universal pattern for scaling TUIs
2. **Modal dialogs** handle focused tasks without disrupting context
3. **Command palette** is the power user's escape hatch
4. **Toggle-able panels** work for optional data displays
5. **Efficient updates** (`batch_update()`) prevent flicker in data-heavy views

---

## Per-Feature TUI Layout Examples

Layout mockups for every feature in `explanation/`. Each shows where the feature surfaces in the TUI, which mode it belongs to, and how the user interacts with it.

> **Legend:**  
> `●` healthy  `◑` degraded  `✕` failed  `◌` unknown  
> `[✓]` enabled  `[ ]` disabled  `[▼]` dropdown  
> `───` separator  `│` border  `→` navigation  

---

### 01 — Streamable HTTP Transport

**Where:** Dashboard mode → Backend Status panel  
**Impact:** New transport badge on backend entries; no dedicated screen needed.

```
┌─── Dashboard ───────────────────────────────────────────────────────┐
│  Mode: [Dashboard]  [Tools]  [Registry]  [Settings]                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── Backend Status ────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Name               Transport      Status    Tools   Latency  │  │
│  │  ──────────────────────────────────────────────────────────── │  │
│  │  github-server       SSE            ● Ready    12     142ms   │  │
│  │  cloud-api           StreamableHTTP ● Ready     8      89ms   │  │
│  │  local-tools         stdio          ● Ready     5      12ms   │  │
│  │  legacy-server       SSE            ◑ Degraded  3    5200ms   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Transport column shows: stdio │ SSE │ StreamableHTTP               │
│  No new screen needed — just a new enum value in the backend list.  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 02 — Conflict Resolution Strategies

**Where:** Settings mode → General tab + Tools mode (conflict indicators)  
**Impact:** Settings dropdown for strategy selection; conflict badges in tool list.

**Settings — Strategy Selection:**

```
┌─── Settings ────────────────────────────────────────────────────────┐
│  Mode: [Dashboard]  [Tools]  [Registry]  [Settings]                 │
├─────────────────────────────────────────────────────────────────────┤
│  [General]  [Timeouts]  [Features]  [Logs]  [About]                 │
│                                                                     │
│  ┌─── Conflict Resolution ───────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Strategy:    [prefix     ▼]                                  │  │
│  │               ┌──────────────────┐                            │  │
│  │               │ ● prefix         │  Auto-prefix with server   │  │
│  │               │ ○ priority       │  Ranked server order       │  │
│  │               │ ○ first_wins     │  First registered wins     │  │
│  │               │ ○ manual         │  Explicit mapping          │  │
│  │               │ ○ error          │  Fail on conflict          │  │
│  │               └──────────────────┘                            │  │
│  │                                                               │  │
│  │  Separator:   [___________]       (used with prefix strategy) │  │
│  │                                                               │  │
│  │  Priority Order (drag to reorder):                            │  │
│  │    1. github-server                                           │  │
│  │    2. database-server                                         │  │
│  │    3. search-server                                           │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Tools Mode — Conflict Indicators:**

```
┌─── Tools ───────────────────────────────────────────────────────────┐
│  [All Tools]  [By Server]  [Conflicts]                              │
│                                                                     │
│  Strategy: prefix  │  3 conflicts resolved  │  42 tools total       │
│                                                                     │
│  Tool Name              Server          Original     Resolved Name  │
│  ─────────────────────────────────────────────────────────────────  │
│  github_search          github-server   search       github_search  │
│  jira_search            jira-server     search       jira_search    │
│  github_create_issue    github-server   create_issue (no conflict)  │
│  db_query               database        query        db_query       │
│  slack_query            slack-server    query        slack_query    │
│                                                                     │
│  [Enter] Details  [C] Show Conflicts Only                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 03 — Tool Filtering (Allow/Deny Lists)

**Where:** Tools mode → Per-server filter panel; also in server detail modal.  
**Impact:** Filter controls per backend, hidden tools shown as greyed-out.

**Tools Mode — Filter View:**

```
┌─── Tools ───────────────────────────────────────────────────────────┐
│  [All Tools]  [By Server]  [Filtered]                               │
│                                                                     │
│  Server: [github-server ▼]   Filter Mode: [allow ▼]                 │
│                                                                     │
│  ┌─── Advertised (allowed) ──────────────────────────────────────┐  │
│  │  [✓] search_issues       Search GitHub issues by query        │  │
│  │  [✓] create_pr           Create a new pull request            │  │
│  │  [✓] list_repos          List repositories for a user         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Hidden (filtered out) ─────────────────── dimmed ──────────┐  │
│  │  [ ] delete_repo         Delete a repository         ⚠ deny   │  │
│  │  [ ] transfer_repo       Transfer repo ownership     ⚠ deny   │  │
│  │  [ ] update_webhook      Modify webhook config       ⚠ deny   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Showing 3 of 6 tools │ 3 hidden by filter                          │
│                                                                     │
│  [Space] Toggle  [A] Allow Mode  [D] Deny Mode  [S] Save            │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 04 — Tool Renaming / Description Override

**Where:** Tools mode → tool detail panel; Settings mode → override editor.  
**Impact:** Inline rename/description edit with live preview of how clients see it.

**Tools Mode — Rename Inline:**

```
┌─── Tools ──── Tool Detail ──────────────────────────────────────────┐
│                                                                     │
│  Server: github-server          Tool: search                        │
│                                                                     │
│  ┌─── Identity ──────────────────────────────────────────────────┐  │
│  │  Original name:  search                                       │  │
│  │  Display name:   [github_search___________]  ✎ renamed        │  │
│  │                                                               │  │
│  │  Original desc:  "Search for things"                          │  │
│  │  Display desc:   [Search GitHub issues, PRs, and repos by     │  │
│  │                   natural-language query. Returns top 25.__   │  │
│  │                                              ✎ overridden     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Client Preview ────────────────────────────────────────────┐  │
│  │  Clients will see:                                            │  │
│  │    name: "github_search"                                      │  │
│  │    desc: "Search GitHub issues, PRs, and repos by…"           │  │
│  │    server: github-server (routed transparently)               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [Enter] Save  [Esc] Cancel  [R] Reset to Original                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 05 — Composite Tool Workflows

**Where:** Dedicated "Workflows" tab within Tools mode; execution monitor in Dashboard.  
**Impact:** DAG builder/viewer for multi-step tool chains, live execution trace.

**Tools Mode — Workflow Editor:**

```
┌─── Tools ──── Workflows ────────────────────────────────────────────┐
│  Workflows: deploy-review ▼     [+ New]  [Import YAML]              │
│                                                                     │
│  ┌─── DAG View ──────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │    ┌──────────┐     ┌──────────┐                              │  │
│  │    │  tests   │     │   lint   │      Level 0 (parallel)      │  │
│  │    │ ci/run   │     │ ci/lint  │                              │  │
│  │    └────┬─────┘     └────┬─────┘                              │  │
│  │         │                │                                    │  │
│  │         └───────┬────────┘                                    │  │
│  │                 ▼                                             │  │
│  │           ┌──────────┐                                        │  │
│  │           │  deploy  │           Level 1 (depends on L0)      │  │
│  │           │ dep/run  │                                        │  │
│  │           │ if: both │                                        │  │
│  │           │  pass ✓  │                                        │  │
│  │           └──────────┘                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Steps: 3 │ Levels: 2 │ Failure mode: abort                         │
│                                                                     │
│  [Enter] Run  [E] Edit YAML  [V] Toggle DAG/List  [D] Delete        │
└─────────────────────────────────────────────────────────────────────┘
```

**Dashboard — Workflow Execution Monitor:**

```
┌─── Dashboard ──── Active Workflows ─────────────────────────────────┐
│                                                                     │
│  ▶ deploy-review  (running)      started: 12:04:31                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [●] tests    ██████████████████████░░  87%   3.2s           │   │
│  │  [●] lint     ████████████████████████  done   1.8s          │   │
│  │  [◌] deploy   waiting on: tests                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [L] View Log  [X] Abort  [Esc] Dismiss                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 06 — Optimizer (find_tool / call_tool Meta-Tools)

**Where:** Dashboard mode → optimizer stats panel; Settings mode → toggle & config.  
**Impact:** Token savings gauge, meta-tool status, search test interface.

**Dashboard — Optimizer Stats:**

```
┌─── Dashboard ──── Optimizer ────────────────────────────────────────┐
│                                                                     │
│  Optimizer: [✓] Enabled       Store: SQLite FTS5                    │
│                                                                     │
│  ┌─── Token Savings ─────────────────────────────────────────────┐  │
│  │  Baseline (all tools):  187 tools │ ~24,800 tokens            │  │
│  │  Optimized (on demand):   avg 5   │    ~680 tokens            │  │
│  │                                                               │  │
│  │  Savings: ██████████████████████████████████░░  97.3%         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Meta-Tools Exposed ────────────────────────────────────────┐  │
│  │  find_tool(query, limit)  — semantic search across catalog    │  │
│  │  call_tool(name, args)    — dynamic invocation → backend      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Test Search ───────────────────────────────────────────────┐  │
│  │  Query: [search github issues________]  Limit: [5]            │  │
│  │                                                               │  │
│  │  Results:                                                     │  │
│  │    1. github_search_issues   (github-server)     score: 0.94  │  │
│  │    2. jira_search            (jira-server)       score: 0.67  │  │
│  │    3. linear_search_issues   (linear-server)     score: 0.61  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [T] Test Query  [R] Rebuild Index  [Esc] Back                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 07 — Incoming Authentication

**Where:** Settings mode → Security tab; Dashboard → auth status badge.  
**Impact:** Auth provider config, connected-client identity display.

**Settings Mode — Auth Configuration:**

```
┌─── Settings ──── Security ──── Incoming Auth ───────────────────────┐
│                                                                     │
│  Auth Mode: [OIDC / OAuth2 ▼]                                       │
│                                                                     │
│  ┌─── OIDC Provider ─────────────────────────────────────────────┐  │
│  │  Issuer URL:    [https://auth.example.com/______________]     │  │
│  │  Audience:      [mcp-sentinel______]                          │  │
│  │  JWKS endpoint: (auto-discovered)  ●                          │  │
│  │  Required claims: iss ✓  aud ✓  exp ✓  nbf ✓                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Options:                                                           │
│  ├── [OIDC / OAuth2]   External IdP (Okta, Auth0, Azure AD)         │
│  ├── [Local JWT]       Self-signed tokens, shared secret / RSA      │
│  └── [Anonymous]       No auth — dev/trusted only          ⚠        │
│                                                                     │
│  [S] Save  [T] Test Connection  [Esc] Cancel                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Dashboard — Auth Status Badge:**

```
┌─── Dashboard ──── header bar ───────────────────────────────────────┐
│  MCP Sentinel    Servers: 5 ●    Auth: OIDC ●    Clients: 3         │
│                                                                     │
│  Connected Clients:                                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  User            Provider   Roles         Connected          │   │
│  │  alice@corp.io   Okta       admin,dev     12:01:04           │   │
│  │  bob@corp.io     Okta       dev           12:03:22           │   │
│  │  service-bot     Local JWT  automation    11:58:00           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 08 — Outgoing Authentication (Backend Credentials)

**Where:** Settings mode → per-server auth config; Dashboard → credential status.  
**Impact:** Per-backend credential strategy selector, token cache status display.

**Settings Mode — Per-Server Outgoing Auth:**

```
┌─── Settings ──── Servers ──── github-server ──── Outgoing Auth ─────┐
│                                                                     │
│  Auth Strategy: [Static Headers ▼]                                  │
│                                                                     │
│  ┌─── Static Headers ───────────────────────────────────────────┐   │
│  │  Authorization:  [Bearer ghp_****xxxx]  👁 Show  🔒 Stored    │   │
│  │  X-Custom:       [________________]   (optional)             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Available Strategies:                                              │
│  ├── [Static Headers]       Fixed key-value per request             │
│  ├── [Token Exchange]       RFC 8693 — swap user token → backend    │
│  └── [Client Credentials]   OAuth2 machine-to-machine               │
│                                                                     │
│  Token Cache:  12 cached │ 3 expired │ TTL: auto (from token exp)   │
│                                                                     │
│  [S] Save  [T] Test Auth  [C] Clear Cache  [Esc] Cancel             │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 09 — Authorization (Policy-Based Access Control)

**Where:** Settings mode → Security → Policies tab; Tools mode → permission badges.  
**Impact:** Policy editor, role-tool matrix view, per-tool access indicators.

**Settings Mode — Policy Editor:**

```
┌─── Settings ──── Security ──── Authorization ───────────────────────┐
│                                                                     │
│  Backend: [Cedar ▼]            Policy File: policies.cedar          │
│                                                                     │
│  ┌─── Role → Permission Matrix ─────────────────────────────────┐   │
│  │                   tools/  tools/  resources/  prompts/       │   │
│  │  Role             list    call    read        read           │   │
│  │  ─────────────────────────────────────────────────           │   │
│  │  admin            ✓       ✓       ✓           ✓             │   │
│  │  developer         ✓       ✓       ✓           ✓            │   │
│  │  readonly          ✓       ✗       ✓           ✓            │   │
│  │  automation        ✗       ✓       ✗           ✗            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─── Tool-Level Overrides ─────────────────────────────────────┐   │
│  │  ⚠ destructive tools → deny ALL roles:                       │   │
│  │    delete_repo, drop_database, rm_rf                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [E] Edit Policy  [V] Validate  [S] Save  [Esc] Cancel              │
└─────────────────────────────────────────────────────────────────────┘
```

**Tools Mode — Permission Badges:**

```
┌─── Tools ──────────────────────────────────────────────────────────┐
│  Tool                  Server          Your Access                 │
│  search_issues         github          ✓ allowed                   │
│  create_pr             github          ✓ allowed                   │
│  delete_repo           github          ✗ denied (policy)           │
│  deploy_prod           deploy-svc      ✗ denied (role: readonly)   │
│  run_tests             ci-server       ✓ allowed                   │
└────────────────────────────────────────────────────────────────────┘
```

---

### 10 — Audit Logging (Structured Events)

**Where:** Dashboard mode → live audit feed; dedicated Logs tab.  
**Impact:** Real-time scrolling event log with filters, export controls.

**Dashboard — Live Audit Feed:**

```
┌─── Dashboard ──── Audit Log ────────────────────────────────────────┐
│  Filter: [All ▼]  User: [*______]  Server: [*______]  ⏸ Pause       │
│                                                                     │
│  Time       User          Method       Tool              Srv   ms   │
│  ────────── ───────────── ──────────── ───────────────── ───── ───  │
│  10:30:01   alice@corp    tools/call   search_issues     gh    142  │
│  10:30:00   bob@corp      tools/list   —                 all    23  │
│  10:29:58   alice@corp    tools/call   create_pr         gh    310  │
│  10:29:55   service-bot   tools/call   run_tests         ci    890  │
│  10:29:42   bob@corp      tools/call   delete_repo       gh    ✗    │
│             └─ denied by policy: destructive tool                   │
│  10:29:40   alice@corp    resources    read_config       cfg    45  │
│  ···                                                                │
│                                                                     │
│  Events: 2,847 │ Errors: 12 │ Denied: 3                             │
│                                                                     │
│  [F] Filter  [E] Export JSON  [/] Search  [Esc] Back                │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 11 — OpenTelemetry Integration

**Where:** Dashboard mode → metrics panel; Settings mode → telemetry config.  
**Impact:** Live metrics gauges, trace waterfall per request, exporter config.

**Dashboard — Metrics Panel:**

```
┌─── Dashboard ──── Telemetry ────────────────────────────────────────┐
│  OTel: ● active    Exporter: OTLP (gRPC)    Prometheus: :9090/m     │
│                                                                     │
│  ┌─── Request Metrics ───────────────────────────────────────────┐  │
│  │  Total requests (1h):   1,204     Errors: 18 (1.5%)           │  │
│  │  Avg latency:           87ms      P99:    420ms               │  │
│  │  Active sessions:       3                                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Per-Backend Breakdown ─────────────────────────────────────┐  │
│  │  Backend         Calls    Avg ms   Err%   Health              │  │
│  │  github-server    482      92      0.8%   ●                   │  │
│  │  ci-server        310     145      2.1%   ◑                   │  │
│  │  deploy-svc       102     210      4.2%   ◑                   │  │
│  │  db-server        310      34      0.3%   ●                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Last Trace ── search_issues ───────────────────────────────┐  │
│  │  ├── middleware      ██░░░░░░░░░░░░░░░░░░░░░  4ms             │  │
│  │  ├── routing         ░██░░░░░░░░░░░░░░░░░░░░  6ms             │  │
│  │  ├── backend_call    ░░░████████████████░░░░░  78ms           │  │
│  │  └── response_parse  ░░░░░░░░░░░░░░░░░░░██░░  8ms             │  │
│  │                      Total: 96ms                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [M] Metrics  [T] Traces  [C] Configure  [Esc] Back                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 12 — Server Groups

**Where:** Dashboard mode → sidebar navigation; Settings mode → group editor.  
**Impact:** Collapsible group tree in sidebar, batch operations per group.

**Dashboard — Grouped Sidebar:**

```
┌─── Dashboard ───────────────────────────────────────────────────────┐
│ ┌─ Servers ───────────┐ ┌─ Detail ────────────────────────────────┐ │
│ │                     │ │                                         │ │
│ │ ▼ development (3)   │ │  Group: development                     │ │
│ │   ● local-db        │ │  Servers: 3  │  Healthy: 2  │  ◑ 1      │ │
│ │   ● test-api        │ │                                         │ │
│ │   ◑ staging-svc     │ │  Actions:                               │ │
│ │                     │ │  [Restart All]  [Stop All]  [Health]    │ │
│ │ ▶ production (2)   │ │                                         │ │
│ │                     │ │  ┌── Servers ───────────────────────┐   │ │
│ │ ▶ ai-tools (4)     │ │  │  ● local-db      stdio   3 tools │   │ │
│ │                     │ │  │  ● test-api      SSE     8 tools │   │ │
│ │ ▶ databases (2)    │ │  │  ◑ staging-svc   HTTP    5 tools │   │ │
│ │                     │ │  └──────────────────────────────────┘   │ │
│ │ ── ungrouped ──     │ │                                         │ │
│ │   ● misc-server     │ │                                         │ │
│ │                     │ │                                         │ │
│ └─────────────────────┘ └─────────────────────────────────────────┘ │
│                                                                     │
│  [G] Manage Groups  [N] New Group  [Enter] Select                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 13 — MCP Server Registry

**Where:** Dedicated Registry mode (4th main mode); add-to-config modal.  
**Impact:** Browsable server catalog with search, install, and version info.

**Registry Mode — Browse Catalog:**

```
┌─── Registry ────────────────────────────────────────────────────────┐
│  Source: toolhive-registry ▼     [+ Add Registry]                   │
│  Search: [github__________________]   Category: [All ▼]             │
│                                                                     │
│  ┌─── Results (3 of 127 servers) ────────────────────────────────┐  │
│  │                                                               │  │
│  │  📦 github-mcp-server                          v2.1.0         │  │
│  │     GitHub API tools: issues, PRs, repos, search              │  │
│  │     Transport: stdio (container)  │  Tools: 14                │  │
│  │     Tags: git, code, github                     [+ Install]   │  │
│  │                                                               │  │
│  │  📦 github-search                               v1.3.2        │  │
│  │     Semantic code search across GitHub repos                  │  │
│  │     Transport: SSE (remote)       │  Tools: 3                 │  │
│  │     Tags: search, code                          [+ Install]   │  │
│  │                                                               │  │
│  │  📦 github-actions-server                       v0.8.1        │  │
│  │     Manage GitHub Actions workflows and runs                  │  │
│  │     Transport: streamable-http    │  Tools: 9                 │  │
│  │     Tags: ci, github, automation                [+ Install]   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  [Enter] Details  [I] Install  [/] Search  [Esc] Back               │
└─────────────────────────────────────────────────────────────────────┘
```

**Registry — Server Detail Modal:**

```
┌─── Server Detail ── github-mcp-server ──────────────────────────────┐
│                                                                     │
│  Version: 2.1.0 (latest)     Published: 2025-06-15                  │
│  Transport: stdio            Package: ghcr.io/github/mcp:2.1.0      │
│                                                                     │
│  Description:                                                       │
│  Full GitHub API integration — issues, pull requests, repos,        │
│  code search, and organization management.                          │
│                                                                     │
│  ┌─── Tools (14) ───────────────────────────────────────────────┐   │
│  │  search_issues    create_pr       list_repos    get_commit   │   │
│  │  create_issue     merge_pr        fork_repo     get_diff     │   │
│  │  search_code      review_pr       create_repo   get_tree     │   │
│  │  list_prs         close_issue                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Versions: 2.1.0  2.0.3  2.0.0  1.5.2  1.4.0                        │
│                                                                     │
│  [I] Add to Config  [V] Change Version  [Esc] Close                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 14 — Client Auto-Configuration

**Where:** Dashboard mode → "Export Config" action; Command Palette shortcut.  
**Impact:** Client picker with preview, copy-to-clipboard, and direct write.

**Dashboard — Export Client Config Modal:**

```
┌─── Export Client Config ────────────────────────────────────────────┐
│                                                                     │
│  MCP Sentinel endpoint: http://localhost:8080/sse                   │
│                                                                     │
│  Detected Clients:                                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [●] VS Code (GitHub Copilot)   ~/.vscode/settings.json      │   │
│  │  [●] Cursor                     ~/.cursor/mcp.json           │   │
│  │  [●] Claude Code                ~/.claude/claude_desktop_…   │   │
│  │  [ ] Claude Desktop             (not detected)               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Selected: Cursor                                                   │
│                                                                     │
│  ┌─── Preview ──────────────────────────────────────────────────┐   │
│  │  {                                                           │   │
│  │    "mcpServers": {                                           │   │
│  │      "mcp-sentinel": {                                       │   │
│  │        "url": "http://localhost:8080/sse",                   │   │
│  │        "transport": "sse"                                    │   │
│  │      }                                                       │   │
│  │    }                                                         │   │
│  │  }                                                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [W] Write to File  [C] Copy to Clipboard  [Esc] Cancel             │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 15 — Health Checks & Circuit Breaker

**Where:** Dashboard mode → server status panel; Settings mode → thresholds.  
**Impact:** Per-backend health indicators, circuit breaker state, probe history.

**Dashboard — Health Status Panel:**

```
┌─── Dashboard ──── Health ───────────────────────────────────────────┐
│  Healthy: 3   Degraded: 1   Unhealthy: 1   Unknown: 0               │
│                                                                     │
│  ┌─── Backend Health ───────────────────────────────────────────┐   │
│  │  Server          State       Circuit   Last Ping   Latency   │   │
│  │  ────────────── ─────────── ───────── ─────────── ────────── │   │
│  │  github-server   ● healthy   CLOSED    10:30:01    42ms      │   │
│  │  ci-server       ● healthy   CLOSED    10:30:02    88ms      │   │
│  │  deploy-svc      ◑ degraded  CLOSED    10:30:01    5,200ms   │   │
│  │  db-server       ● healthy   CLOSED    10:30:03    12ms      │   │
│  │  old-api         ✕ unhealthy OPEN      10:28:45    timeout   │   │
│  │                  └─ 3/3 failures │ cooldown: 45s remaining   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─── Circuit Breaker ────────────────────────────────────────────┐ │
│  │  old-api:  CLOSED ──▶ 3 failures ──▶ OPEN ──▶ 15s…HALF-OPEN │ │
│  │            ████████    ███✕✕✕         ████      probing…      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Check interval: 30s │ Failure threshold: 3 │ Cooldown: 60s         │
│                                                                     │
│  [P] Ping Now  [R] Reset Circuit  [C] Configure  [Esc] Back         │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 16 — Middleware Chain Architecture

**Where:** Settings mode → Pipeline tab; Dashboard → middleware trace per request.  
**Impact:** Visual pipeline editor, per-layer toggle, request flow trace.

**Settings Mode — Middleware Pipeline:**

```
┌─── Settings ──── Middleware Pipeline ───────────────────────────────┐
│                                                                     │
│  Request flows top → bottom. Drag to reorder. Toggle to disable.    │
│                                                                     │
│  ┌─── Pipeline ──────────────────────────────────────────────────┐  │
│  │    #   Layer                Status                            │  │
│  │   ─── ──────────────────── ──────                             │  │
│  │    1   Recovery             [✓] always on                     │  │
│  │    2   Header Validation    [✓]                               │  │
│  │    3   Authentication       [✓] OIDC                          │  │
│  │    4   Authorization        [✓] Cedar                         │  │
│  │    5   Audit Logger         [✓]                               │  │
│  │    6   Telemetry            [✓] OTLP                          │  │
│  │    7   Discovery            [✓]                               │  │
│  │    8   MCP Parsing          [✓] always on                     │  │
│  │    9   Tool Filter          [✓] 2 servers configured          │  │
│  │   10   Tool Call Filter     [ ] disabled                      │  │
│  │   11   Backend Router       [✓] always on                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Active: 10/11 │ Custom middleware: 0                               │
│                                                                     │
│  [Space] Toggle  [↑↓] Reorder  [Enter] Configure  [S] Save          │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 17 — Backend Status Model

**Where:** Dashboard mode → server list; server detail modal → conditions log.  
**Impact:** Rich lifecycle phases replace binary connected/failed indicators.

**Dashboard — Multi-Phase Server List:**

```
┌─── Dashboard ──── Servers ──────────────────────────────────────────┐
│                                                                     │
│  Server            Phase          Since       Tools   Latency       │
│  ──────────────── ────────────── ─────────── ─────── ───────────    │
│  github-server     ● Ready        10:00:00    14      42ms          │
│  ci-server         ● Ready        10:00:01    8       88ms          │
│  deploy-svc        ◑ Degraded     10:28:30    5       5,200ms       │
│  db-server         ● Ready        10:00:02    6       12ms          │
│  old-api           ✕ Failed       10:28:45    —       —             │
│  new-svc           ◌ Pending      10:31:00    —       —             │
│  staging           ⟳ Initializing 10:31:05    …       connecting    │
│                                                                     │
│  Phases: ● Ready=3  ◑ Degraded=1  ✕ Failed=1  ◌ Pending=1  ⟳ 1     │
└─────────────────────────────────────────────────────────────────────┘
```

**Server Detail — Conditions Log:**

```
┌─── deploy-svc ──── Status Detail ───────────────────────────────────┐
│                                                                     │
│  Phase: ◑ Degraded                                                  │
│                                                                     │
│  ┌─── Conditions ───────────────────────────────────────────────┐   │
│  │  10:30:01  ⚠ HealthCheck  Response time 5200ms > 5000ms      │   │
│  │  10:29:30  ✓ HealthCheck  Healthy, 142ms                     │   │
│  │  10:29:00  ✓ HealthCheck  Healthy, 98ms                      │   │
│  │  10:00:00  ✓ Connected    Capabilities: 5 tools, 1 resource  │   │
│  │  09:59:58  ℹ Initializing  Connecting via streamable-http    │   │
│  │  09:59:55  ℹ Pending       Loaded from config                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [R] Restart  [D] Disconnect  [H] Force Health Check  [Esc] Back    │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 18 — Secret Management

**Where:** Settings mode → Secrets tab; server config → secret reference picker.  
**Impact:** Encrypted secret store UI, reference syntax, masked display.

**Settings Mode — Secrets Manager:**

```
┌─── Settings ──── Secrets ───────────────────────────────────────────┐
│                                                                     │
│  Store: AES-256-GCM (local)     [Unlock 🔓]                         │
│                                                                     │
│  ┌─── Stored Secrets ──────────────────────────────────────────┐    │
│  │  Name               Source         Used By        Last Set  │    │
│  │  ──────────────────  ───────────── ────────────── ───────── │    │
│  │  github_token        keyring       github-server  Jun 15    │    │
│  │  db_password         encrypted     db-server      Jun 10    │    │
│  │  openai_key          env: $OAI_KEY ai-server      Jun 20    │    │
│  │  deploy_credentials  1password     deploy-svc     Jun 18    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Config reference syntax:  {{ secrets.github_token }}               │
│                                                                     │
│  [N] New Secret  [E] Edit  [D] Delete  [R] Rotate  [Esc] Back       │
└─────────────────────────────────────────────────────────────────────┘
```

**Server Config — Secret Reference:**

```
┌─── Server Config ── github-server ──────────────────────────────────┐
│                                                                     │
│  Headers:                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Authorization: [{{ secrets.github_token }}]  🔒 referenced  │   │
│  │                  resolved: Bearer ghp_****xxxx   👁 peek     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [S] Save  [P] Pick Secret  [Esc] Cancel                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 19 — Session Management

**Where:** Dashboard mode → active sessions panel; session detail modal.  
**Impact:** Per-client session list, routing table view, TTL countdown.

**Dashboard — Active Sessions:**

```
┌─── Dashboard ──── Sessions ────────────────────────────────────────┐
│                                                                    │
│  Active: 3     Expired (1h): 7     TTL: 30m                        │
│                                                                    │
│  ┌─── Live Sessions ───────────────────────────────────────────┐   │
│  │  Session ID         User          Tools  Created    TTL     │   │
│  │  ──────────────── ─────────────── ──── ─────────── ──────   │   │
│  │  mcp-sess-a1b2     alice@corp     32    10:01:04    28:03   │   │
│  │  mcp-sess-c3d4     bob@corp       32    10:03:22    26:41   │   │
│  │  mcp-sess-e5f6     service-bot    18    09:58:00    01:59   │   │
│  │                                          │ ⚠ expiring soon  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  [Enter] Session Detail  [K] Kill Session  [Esc] Back              │
└────────────────────────────────────────────────────────────────────┘
```

**Session Detail Modal:**

```
┌─── Session ── mcp-sess-a1b2 ────────────────────────────────────────┐
│                                                                     │
│  User: alice@corp     Created: 10:01:04     TTL remaining: 28:03    │
│  Immutable: ✓         Session header: Mcp-Session-Id                │
│                                                                     │
│  ┌─── Routing Table (frozen at creation) ──────────────────────┐    │
│  │  Tool                  → Backend           Affinity         │    │
│  │  search_issues         → github-server     sticky           │    │
│  │  create_pr             → github-server     sticky           │    │
│  │  run_tests             → ci-server         sticky           │    │
│  │  deploy_staging        → deploy-svc        sticky           │    │
│  │  … (28 more)                                                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Calls this session: 14  │  Errors: 0  │  Avg latency: 76ms         │
│                                                                     │
│  [K] Kill  [R] Refresh TTL  [Esc] Close                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 20 — Config Format & Validation

**Where:** Settings mode → Config tab; startup validation toast.  
**Impact:** YAML editor with live validation, schema errors highlighted inline.

**Settings Mode — Config Editor:**

```
┌─── Settings ──── Config ────────────────────────────────────────────┐
│  Format: [YAML ▼]   File: config.yaml   Schema: v2                  │
│                                                                     │
│  ┌─── Editor ───────────────────────────────────── Validation ──┐   │
│  │  1 │ # MCP Sentinel Configuration             │  ✓ Valid     │   │
│  │  2 │ version: 2                               │              │   │
│  │  3 │ global:                                  │  Warnings:   │   │
│  │  4 │   timeout: 30s                           │  L12: no     │   │
│  │  5 │   partial_failure: continue              │  auth set    │   │
│  │  6 │                                          │              │   │
│  │  7 │ mcpServers:                              │  Errors:     │   │
│  │  8 │   github-server:                         │  (none)      │   │
│  │  9 │     command: python                      │              │   │
│  │ 10 │     args: ["-m", "github_mcp"]           │              │   │
│  │ 11 │     timeout: 60s  # override global      │              │   │
│  │ 12 │     # auth: TODO                         │              │   │
│  │ 13 │   ci-server:                             │              │   │
│  │ 14 │     url: http://ci:8080/mcp              │              │   │
│  │ 15 │     transport: streamable-http           │              │   │
│  └───────────────────────────────────── ────────────────────────┘   │
│                                                                     │
│  [S] Save  [V] Validate  [J] Convert to JSON  [I] Import  [Esc]     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 21 — Skills System

**Where:** Registry mode → Skills tab; Dashboard → quick-apply presets.  
**Impact:** Curated preset browser that auto-configures servers and tools.

**Registry Mode — Skills Browser:**

```
┌─── Registry ──── Skills ────────────────────────────────────────────┐
│  Search: [________________]   Category: [All ▼]                     │
│                                                                     │
│  ┌─── Available Skills ─────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  🎯 Code Review                                     [Apply]  │   │
│  │     Servers: github-mcp, diff-analyzer, lint-server          │   │
│  │     Tools: 8  │  Tags: code, review, quality                 │   │
│  │                                                              │   │
│  │  🎯 Data Analysis                                   [Apply]  │   │
│  │     Servers: sql-server, pandas-mcp, chart-gen               │   │
│  │     Tools: 12 │  Tags: data, sql, visualization              │   │
│  │                                                              │   │
│  │  🎯 DevOps                                          [Apply]  │   │
│  │     Servers: docker-mcp, k8s-server, ci-runner               │   │
│  │     Tools: 15 │  Tags: infra, deploy, monitoring             │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Active Skills: Code Review ✓                                       │
│                                                                     │
│  [Enter] Details  [A] Apply Skill  [R] Remove  [Esc] Back           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 22 — Version Drift Detection

**Where:** Dashboard mode → update badges on server list; notification toast.  
**Impact:** Per-server version comparison badge, one-click update action.

**Dashboard — Version Drift Indicators:**

```
┌─── Dashboard ──── Servers ──────────────────────────────────────────┐
│                                                                     │
│  Server            Version    Registry    Status                    │
│  ──────────────── ────────── ────────── ──────────────────────      │
│  github-server     v2.1.0     v3.0.0     ⬆ Update available         │
│  ci-server         v1.5.2     v1.5.2     ✓ Up to date               │
│  deploy-svc        v0.8.1     v1.0.0     ⬆ Major update             │
│  db-server         v4.2.0     v4.2.1     ⬆ Patch available          │
│  local-tools       (local)    —          — No registry              │
│                                                                     │
│  Updates available: 3 of 5 servers                                  │
│                                                                     │
│  [U] Update Selected  [A] Update All  [C] View Changelog            │
└─────────────────────────────────────────────────────────────────────┘
```

**Update Changelog Modal:**

```
┌─── github-server ── v2.1.0 → v3.0.0 ───────────────────────────────┐
│                                                                    │
│  ⚠ MAJOR version change — may include breaking changes             │
│                                                                    │
│  Changelog:                                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  v3.0.0 — Breaking: renamed search → search_issues           │  │
│  │  v2.2.0 — Added: list_workflows, get_actions                 │  │
│  │  v2.1.1 — Fixed: pagination in search results                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  [U] Update Now  [S] Skip Version  [Esc] Cancel                    │
└────────────────────────────────────────────────────────────────────┘
```

---

### 23 — Graceful Exit with Resume

**Where:** Settings mode → Startup tab; exit confirmation dialog.  
**Impact:** Per-server "start on launch" toggle, exit state persistence.

**Settings Mode — Startup Behavior:**

```
┌─── Settings ──── Startup ───────────────────────────────────────────┐
│                                                                     │
│  Resume mode: [Restore last session ▼]                              │
│                                                                     │
│  ┌─── Per-Server Launch Behavior ──────────────────────────────┐    │
│  │  Server            Auto-Start   Last State   Transport      │    │
│  │  ──────────────── ─────────── ──────────── ────────────     │    │
│  │  github-server     [✓]          ● running    stdio          │    │
│  │  ci-server         [✓]          ● running    SSE            │    │
│  │  deploy-svc        [ ]          ○ stopped    HTTP           │    │
│  │  db-server         [✓]          ● running    stdio          │    │
│  │  old-api           [ ]          ✕ failed     SSE            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Options:                                                           │
│  ├── [Restore last session]    Resume previously running servers    │
│  ├── [Start all auto-start]    Start servers marked auto-start      │
│  └── [Manual start]            Don't auto-connect on launch         │
│                                                                     │
│  [S] Save  [Esc] Cancel                                             │
└─────────────────────────────────────────────────────────────────────┘
```

**Exit Confirmation:**

```
┌─── Exiting MCP Sentinel ───────────────────────────────────────────┐
│                                                                    │
│  3 servers are currently running.                                  │
│                                                                    │
│  ○  Save state and restore on next launch                          │
│  ○  Stop all servers and exit                                      │
│  ○  Cancel                                                         │
│                                                                    │
│  [Enter] Confirm  [Esc] Cancel                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

### 24 — Network Isolation Configuration

**Where:** Settings mode → per-server Security tab.  
**Impact:** Per-backend network policy controls for sandboxed execution.

**Settings Mode — Per-Server Network Isolation:**

```
┌─── Settings ──── github-server ──── Network Isolation ──────────────┐
│                                                                     │
│  Network Mode: [bridge ▼]                                           │
│                                                                     │
│  ┌─── Allowed Outbound ─────────────────────────────────────────┐   │
│  │  ✓  api.github.com                                           │   │
│  │  ✓  github.com                                               │   │
│  │  ✗  * (all other hosts blocked)                              │   │
│  │                                                              │   │
│  │  [+ Add Host]                                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─── Environment Restrictions ─────────────────────────────────┐   │
│  │  HTTP_PROXY:   [_______________]   (blank = inherit host)    │   │
│  │  NO_PROXY:     [localhost,127.0.0.1]                         │   │
│  │  DNS:          [system ▼]                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Modes: host (no isolation) │ bridge (filtered) │ none (offline)    │
│                                                                     │
│  [S] Save  [T] Test Connectivity  [Esc] Cancel                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 25 — Multiple Registry Sources

**Where:** Registry mode → Sources tab; Settings mode → registry URLs.  
**Impact:** Multi-source registry list with priority ordering and status.

**Settings Mode — Registry Sources:**

```
┌─── Settings ──── Registries ────────────────────────────────────────┐
│                                                                     │
│  ┌─── Configured Sources (priority order) ──────────────────────┐   │
│  │  #  Source              Type       Status     Servers        │   │
│  │  ── ────────────────── ────────── ────────── ────────        │   │
│  │  1  company-registry    API        ● online    42            │   │
│  │  2  toolhive-public     API        ● online    127           │   │
│  │  3  ./local-servers     filesystem ● loaded    5             │   │
│  │  4  github.com/org/reg  git        ● synced    18            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Priority: Higher = checked first for name conflicts                │
│  Total unique servers: 188  │  Duplicates resolved: 4               │
│                                                                     │
│  [+ Add Source]  [↑↓] Reorder Priority  [D] Delete  [S] Save        │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 26 — Background Sync with Change Detection

**Where:** Dashboard mode → sync status indicator; Settings mode → sync config.  
**Impact:** Live config hot-reload indicator, change diff preview.

**Dashboard — Sync Status:**

```
┌─── Dashboard ──── footer bar ───────────────────────────────────────┐
│  Config: config.yaml   Hash: a3f8…c2   Last sync: 10:30:02  ● live  │
│                                                                     │
│  ┌─── Recent Sync Events ───────────────────────────────────────┐   │
│  │  10:30:02  ✓  No changes (hash match)                        │   │
│  │  10:28:02  ⟳  Config changed — reloading…                    │   │
│  │            ├── Added: staging-server (SSE)                   │   │
│  │            ├── Changed: ci-server timeout 30s → 60s          │   │
│  │            └── Removed: old-api                              │   │
│  │  10:26:02  ✓  No changes                                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Settings Mode — Sync Configuration:**

```
┌─── Settings ──── Background Sync ───────────────────────────────────┐
│                                                                     │
│  Hot Reload: [✓] Enabled                                            │
│  Watch file: config.yaml                                            │
│  Interval:   [120] seconds    Jitter: [✓] random ±15s               │
│                                                                     │
│  Change Detection: [hash ▼]                                         │
│  ├── [hash]       Compare SHA-256 before/after (efficient)          │
│  ├── [mtime]      File modification time (fast, less reliable)      │
│  └── [inotify]    OS file watcher (instant, Linux only)             │
│                                                                     │
│  On failure: [exponential backoff ▼]    Max retries: [5]            │
│                                                                     │
│  [S] Save  [F] Force Sync Now  [Esc] Cancel                         │
└─────────────────────────────────────────────────────────────────────┘
```
