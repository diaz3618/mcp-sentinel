# MCP Sentinel Deep Audit and Implementation Playbook

Date: 2026-02-21
Repository: `/home/diaz/git/MCP-Gateway`

## Audit Scope

This audit covers the 8 requested items exactly and does **not** include code changes.
The deliverable is an implementation plan and Copilot playbook prompt.

## Audit Method

- Static code inspection of TUI, CLI, lifecycle, bridge, and capability paths.
- Runtime reproduction in both modes:
  - `python -m mcp_gateway --host 127.0.0.1 --port 9010 --log-level info` (TUI)
  - `python -m mcp_gateway --no-tui --host 127.0.0.1 --port 9011 --log-level info`
- Log forensics on successful and failing runs.
- Cross-reference with Textual documentation/examples and GitHub TUI implementations.

## MCP Server Coverage ("use all available MCP servers")

All configured servers in `config.json` were exercised during runtime startup attempts.

Configured entries:

1. `analyzer` (stdio)
2. `context7` (stdio)
3. `memory-bank-mcp` (stdio)
4. `openai-developer-docs` (stdio)
5. `python-agent-docs-mcpdoc` (stdio)
6. `python-lsp-mcp` (stdio)
7. `sequential-thinking` (stdio)
8. `ripgrep` (invalid entry, missing `type`)

Evidence:

- Loader warning for invalid `ripgrep`: `config.json:60` and `logs/gateway_20260221_001150_INFO.log:21`.
- 7/7 startup attempts visible per-server: `logs/gateway_20260221_001221_INFO.log:35-48`.
- Full-success historical run (used to prove capabilities exist):
  - `logs/gateway_20260220_235626_INFO.log:52` (`Active servers: 7/7`)
  - `logs/gateway_20260220_235626_INFO.log:286` (`Aggregated discovery: 82 tools, 5 resources, 0 prompts`)
  - `logs/gateway_20260220_235626_INFO.log:387` (`Populating TUI tables: 82 tools, 5 resources, 0 prompts`)

## External Reference Baseline (GitHub / Textual)

Relevant references used to avoid guessing implementation:

- Primary validation source for Textual behavior in this audit was the local clone at `repos/textual`, especially `repos/textual/docs/*` and `repos/textual/docs/examples/*`.
- Textual design/themes guide: `repos/textual/docs/guide/design.md`
- Textual command palette guide: `repos/textual/docs/guide/command_palette.md`
- Textual print-capture pattern: `repos/textual/tests/snapshot_tests/snapshot_apps/capture_print.py`
- Textual theme example app: `repos/textual/docs/examples/themes/todo_app.py`
- Similar real-world TUI event screen from GitHub clone: `repos/dolphie/dolphie/Widgets/EventLogScreen.py`

Web references:

- https://textual.textualize.io/guide/design/#__tabbed_1_1
- https://textual.textualize.io/guide/command_palette/
- https://github.com/modelcontextprotocol/python-sdk/issues/521
- https://github.com/modelcontextprotocol/python-sdk/issues/552
- https://github.com/modelcontextprotocol/python-sdk/issues/835

## Validation Pass Against Local Textual Docs (Results)

Validated directly against `repos/textual/docs` and `repos/textual/src`:

- Command palette theme behavior is built in when app commands include `yield from super().get_system_commands(screen)`:
  - built-in `Theme` system command: `repos/textual/src/textual/app.py:1283-1288`
  - `action_change_theme` calls theme search: `repos/textual/src/textual/app.py:1767-1769`
  - theme search uses `ThemeProvider` from `App.available_themes`: `repos/textual/src/textual/app.py:1902-1911`, `repos/textual/src/textual/theme.py:466-480`
- Print capture semantics:
  - App-level capture routes captured stdout/stderr to `events.Print`: `repos/textual/src/textual/app.py:2029-2033`
  - Capture registration API: `repos/textual/src/textual/app.py:2034-2050`
- `OptionList` public APIs exist for selection/highlight logic:
  - read-only `options`: `repos/textual/src/textual/widgets/_option_list.py:300-307`
  - `get_option_index`: `repos/textual/src/textual/widgets/_option_list.py:448-461`
  - `get_option_at_index`: `repos/textual/src/textual/widgets/_option_list.py:463-480`
  - This validates that `ol._options` in current code is private usage and should be removed.
- Theme example set/order in the design guide is explicit:
  - `nord`, `gruvbox`, `tokyo-night`, `textual-dark`, `solarized-light`, `atom-one-dark`, `atom-one-light`
  - source: `repos/textual/docs/guide/design.md:7-40`

---

## Issue 1: stdout/CLI output overlaps the TUI

### Findings

- TUI enables print capture on mount: `mcp_gateway/tui/app.py:177`.
- TUI explicitly does **not** redirect stderr: `mcp_gateway/tui/app.py:179-184`.
- Status callback is cleared before backend shutdown completes: `mcp_gateway/tui/app.py:202-207`.
- When callback suppression is removed, status writes go to terminal `print()`: `mcp_gateway/display/console.py:132-184`.
- Stdio backends are created without explicit `errlog`: `mcp_gateway/bridge/client_manager.py:224`.
- MCP SDK defaults `errlog=sys.stderr` and wires subprocess stderr to it:
  - `/home/diaz/.local/lib/python3.13/site-packages/mcp/client/stdio/__init__.py:106`
  - `/home/diaz/.local/lib/python3.13/site-packages/mcp/client/stdio/__init__.py:251-255`
- In the fresh TUI run (`2026-02-21 00:11`), backend `uv` cache errors printed as raw terminal text while TUI was active, confirming output bleed in practice.

### Root Cause

Output is split across multiple channels with no single owner:

- Textual capture only handles Python-level `print` routed through Textual events.
- Backend subprocess stderr can still hit terminal stderr directly.
- Unmount sequence disables callback/capture too early.

### Implementation Direction

- Introduce a single output pipeline for lifecycle + backend stderr.
- Keep callback and capture active until backend shutdown is complete.
- Pass an explicit, app-controlled stderr sink into stdio backend creation.
- Remove direct `print` fallback while TUI is active.

### Acceptance Criteria

- No terminal text appears on top of TUI while app is running.
- Startup/shutdown/backend messages appear inside Events panel only.

---

## Issue 2: Backend Services shows connected, but Tools/Resources/Prompts are empty

### Findings

- Capability discovery succeeds in full runs:
  - `logs/gateway_20260220_235626_INFO.log:286` (82/5/0)
  - `logs/gateway_20260220_235626_INFO.log:387` (table populate called)
- UI population is gated by exact stage text match:
  - `mcp_gateway/tui/app.py:335` (`if stage == "✅ Service Ready":`)
- Capability registry catches a non-existent exception class:
  - `mcp_gateway/bridge/capability_registry.py:147` (`except mcp_types.Error`)
  - runtime evidence: `AttributeError: module 'mcp.types' has no attribute 'Error'` in multiple logs, e.g. `logs/gateway_20260220_235626_INFO.log:82-110`

### Root Cause

- Discovery data exists, but UI rendering trigger is brittle.
- Exception handling bug introduces noisy failures and weakens discovery reliability.

### Implementation Direction

- Decouple table population from literal stage string.
- Populate tables whenever payload contains `tools/resources/prompts/route_map`.
- Fix capability exception handling to actual SDK exception type(s).
- Add explicit empty-state copy for true zero-capability scenarios.

### Acceptance Criteria

- Nonzero discovered capability counts always produce visible rows and tab counts.
- True zero case shows explicit empty state (not blank/frozen view).

---

## Issue 3: Top toolbar has only one option; create grouped options by category

### Findings

- App currently renders `Header` and `Footer`; no custom top toolbar widget:
  - `mcp_gateway/tui/app.py:71-80`
- Actions exist only as key bindings + command palette entries:
  - bindings: `mcp_gateway/tui/app.py:42-52`
  - commands: `mcp_gateway/tui/app.py:84-127`

### Root Cause

No discoverable top action surface exists.

### Implementation Direction

Add a dedicated top toolbar with grouped controls:

- App: Quit/Shutdown
- Navigation: Tools/Resources/Prompts
- Appearance: Theme picker / Cycle theme
- Diagnostics: Server details / Connection info

Keep key bindings and command palette intact.

### Acceptance Criteria

- Multiple top toolbar controls exist and are grouped by category.
- Toolbar provides equivalents for key workflow actions.

---

## Issue 4: Alignment constraints (top and bottom horizontal alignment)

Required by user:

- Top of Server Info must align with top of Events.
- Bottom of Backend Services must align with bottom of Events.

### Findings

- Layout uses `Horizontal#top-row` with sidebar + main area: `mcp_gateway/tui/app.py:73-79`.
- Sidebar relies on `height:auto`, `max-height`, and `dock: bottom`:
  - `mcp_gateway/tui/gateway.tcss:28-33`
  - `mcp_gateway/tui/gateway.tcss:54-60`

### Root Cause

Current docking/max-height strategy is not deterministic across content and terminal sizes.

### Implementation Direction

Replace docking with explicit sidebar grid/flex distribution:

- Row 1: `ServerInfoWidget` (`auto`)
- Row 2: spacer (`1fr`)
- Row 3: `BackendStatusWidget` (`auto`)

Keep Events pane as full-height sibling in same parent row.

### Acceptance Criteria

- Verified on at least 3 terminal sizes: small, medium, large.
- Alignment remains exact under resize and state changes.

---

## Issue 5: Terminal unusable after TUI quit; `--no-tui` Ctrl+C behavior

### Findings

- `action_quit` exits app immediately after `_stop_server()`:
  - `mcp_gateway/tui/app.py:408-413`
- Server thread is daemonized:
  - `mcp_gateway/tui/app.py:195-199`
- Unmount clears callback before shutdown completes:
  - `mcp_gateway/tui/app.py:202-207`
- Shared `AsyncExitStack` entered in startup tasks and closed later, causing AnyIO cancel-scope failures:
  - stack defined: `mcp_gateway/bridge/client_manager.py:215`
  - entered from startup paths: `mcp_gateway/bridge/client_manager.py:225`, `:229`, `:246`, `:256`, `:260`
  - closed on shutdown: `mcp_gateway/bridge/client_manager.py:397`
- Repeated runtime error across logs:
  - `Attempted to exit cancel scope in a different task than it was entered in`
  - e.g. `logs/gateway_20260221_001221_INFO.log:156`
- Fresh TUI run (`logs/gateway_20260221_001150_INFO.log`) ends with app finished (`:93`) before normal shutdown transcript, confirming lifecycle truncation risk.

### `--no-tui` reproduction notes

- First Ctrl+C did not immediately terminate during backend startup in the reproduction session.
- Second Ctrl+C triggered shutdown output and eventual exit.
- Log still shows same `AsyncExitStack` cleanup error: `logs/gateway_20260221_001221_INFO.log:156`.

### Root Cause

- Lifecycle ownership is inconsistent:
  - daemon thread can terminate out-of-order
  - exit stack contexts are not cleanly owned by one task scope
  - callback/capture cleanup order is incorrect

### Implementation Direction

- Remove cross-task `AsyncExitStack` ownership pattern.
- Ensure enter/exit of async contexts happens in same task context.
- Make quit a two-phase operation: request shutdown, wait for `ServerStopped`, then exit.
- Keep callback/capture active until shutdown fully completes.
- Keep deterministic terminal restoration after confirmed shutdown.

### Acceptance Criteria

- TUI quit returns terminal with visible input every run.
- `--no-tui` exits on first Ctrl+C in normal path.
- No cancel-scope runtime errors in shutdown logs.

---

## Issue 6: Rename to MCP Sentinel, update author/version, remove stale naming

### Findings

Already correct:

- `pyproject.toml:2` name `mcp-sentinel`
- `pyproject.toml:3` version `0.1.0`
- `pyproject.toml:8` author `Daniel Diaz Santiago`
- runtime constants:
  - `mcp_gateway/constants.py:3` (`MCP Sentinel`)
  - `mcp_gateway/constants.py:4` (`0.1.0`)
  - `mcp_gateway/constants.py:5` (`diaz3618`)

Incomplete/stale:

- README still legacy branding/version text:
  - `README.md:1` (`# MCP Gateway`)
  - `README.md:82` (`Start MCP_Bridge_Server v3.0.0`)
- Script alias still exports old name: `pyproject.toml:22` (`mcp-gateway`)
- Package/module namespace still `mcp_gateway` throughout (broad internal usage).
- Logging namespace and filenames still old style:
  - logger names: `mcp_gateway.*` in `mcp_gateway/display/logging_config.py:55-76`
  - filenames `gateway_...` in `mcp_gateway/display/logging_config.py:116`

### Root Cause

Rename was partial (branding constants/package metadata), not a full migration plan.

### Implementation Direction

Define explicit target scope:

- Branding-only rename (fast, lower risk), or
- Full package rename (`mcp_gateway` -> `mcp_sentinel`) with compatibility shim.

At minimum for current request:

- Clean all user-facing docs/CLI/TUI strings.
- Align README usage/examples/help output with current app names/version.

### Acceptance Criteria

- No stale `MCP Gateway` or `MCP_Bridge_Server` strings in user-facing docs/UI.
- Author appears as requested in docs and runtime.

---

## Issue 7: Better theme management + toolbar option + strict Textual alignment

### Findings

- Theme switch exists via key bindings and modal:
  - `mcp_gateway/tui/app.py:50-52`, `:415-451`
- Theme persistence exists: `mcp_gateway/tui/settings.py:66-89`
- Theme modal uses private `OptionList` internals (`_options`):
  - `mcp_gateway/tui/screens/theme_picker.py:89`
- No top toolbar theme control exists.

### Textual guidance anchors

- Runtime theme changes through `App.theme` and command discoverability:
  - `repos/textual/docs/guide/design.md:42-47`
  - `repos/textual/docs/guide/command_palette.md:33-43`
- Theme variable legibility guidance (`$text`, `$text-muted`, etc.):
  - `repos/textual/docs/guide/design.md:179-183`
- Example cycling themes:
  - `repos/textual/docs/examples/themes/todo_app.py:59-62`, `:90-91`

### Root Cause

Theme functionality exists but UX and implementation quality are inconsistent with Textual best-practice.

### Implementation Direction

- Add dedicated top toolbar "Theme" control.
- Keep command palette entries and improve discoverability labels.
- Preserve Textual built-in theme command behavior by keeping `yield from super().get_system_commands(screen)` intact.
- Remove private API use from theme picker.
- Use public `OptionList` APIs (`options`, `get_option_index`, `get_option_at_index`) instead of `._options`.
- Ensure the user-facing quick theme cycle includes the design-guide example set and order exactly:
  - `nord`, `gruvbox`, `tokyo-night`, `textual-dark`, `solarized-light`, `atom-one-dark`, `atom-one-light`
- Ensure CSS relies on theme variables for contrast safety.

### Acceptance Criteria

- Theme change available from toolbar and command palette.
- Theme persists across runs.
- No private widget internals are used.
- Example theme names from Textual design guide are present and ordered correctly in the quick cycle path.

---

## Issue 8: CLI output must be in Events box; Events scrollable

### Findings

- Events uses `RichLog` with `auto_scroll=True` and capture subclass:
  - `mcp_gateway/tui/widgets/event_log.py:54-60`
  - `mcp_gateway/tui/widgets/event_log.py:36-46`
- Captured output path currently includes only Textual `Print` events + synthesized status lines.
- Backend stderr and late shutdown output can bypass this path (Issue 1).

### Root Cause

Events widget is technically capable, but output routing architecture is incomplete.

### Implementation Direction

- Route all lifecycle and backend process output into one append-only event stream.
- Include timestamps and source tags (`lifecycle`, `backend:<name>`, `shutdown`).
- Keep bounded history and scroll support.

### Acceptance Criteria

- All relevant startup/shutdown/backend output appears in Events.
- Events remains scrollable for long transcripts.
- No external flood into terminal while TUI active.

---

## Cross-Cutting Critical Defects

1. Shared `AsyncExitStack` cross-task ownership (shutdown instability).
2. Output ownership split across callback/print/stderr channels.
3. Brittle UI population trigger based on a literal status string.

These three defects explain most observed user-facing symptoms.

## Recommended Implementation Order

1. Lifecycle/cleanup architecture (Issue 5).
2. Unified output routing into Events (Issues 1 and 8).
3. Capability population hardening + exception fix (Issue 2).
4. Layout and toolbar/theme UX work (Issues 3, 4, 7).
5. Rename/documentation cleanup and consistency pass (Issue 6).

## Additional Risks Identified

- Secrets/API keys are committed in repository configs (`config.json`, `.vscode/mcp.json`).
- `ripgrep` config entry is invalid (`config.json:60-66`), so one expected backend is never loaded.

---

## Copilot Playbook Prompt (Implementation Prompt)

```text
You are implementing a full remediation pass for MCP Sentinel.

Hard requirements:
- Implement all requested items end-to-end; no partial fixes.
- Preserve existing behavior unless a change is required to satisfy these fixes.
- Add tests and runtime validation evidence.

Project files to inspect/update:
- mcp_gateway/tui/app.py
- mcp_gateway/tui/widgets/*
- mcp_gateway/tui/screens/theme_picker.py
- mcp_gateway/tui/gateway.tcss
- mcp_gateway/bridge/client_manager.py
- mcp_gateway/bridge/capability_registry.py
- mcp_gateway/display/console.py
- mcp_gateway/cli.py
- mcp_gateway/display/logging_config.py
- pyproject.toml
- README.md

Goals:
1) Prevent terminal bleed over TUI
- Route backend stdio stderr and lifecycle output into Events.
- Do not allow output to bypass TUI while active.
- Keep capture/callback active until full shutdown completion.

2) Fix Tools/Resources/Prompts population reliability
- Do not gate populate on exact stage string equality.
- Populate when capability payload is present.
- Add explicit empty-state messages for true zero-capability results.
- Fix capability exception handling for current MCP SDK errors.

3) Add a real top toolbar with grouped options
- Categories: App, Navigation, Appearance, Diagnostics.
- Keep key bindings and command palette entries.
- Add toolbar equivalents for major actions.

4) Enforce required panel alignment
- Server Info top aligns with Events top.
- Backend Services bottom aligns with Events bottom.
- Must hold across terminal sizes and resize.

5) Fix shutdown and terminal restore
- Remove shared AsyncExitStack cross-task ownership.
- Ensure async context enter/exit happens in the same task scope.
- Make quit two-phase: request shutdown, wait for confirmation, then exit.
- Ensure --no-tui exits cleanly on first Ctrl+C in normal conditions.
- Ensure no terminal input visibility corruption after quit.

6) Complete MCP Sentinel naming consistency
- Keep version 0.1.0.
- Docs author: Daniel Diaz Santiago.
- CLI/TUI author string: diaz3618.
- Remove stale user-facing MCP Gateway / MCP_Bridge_Server strings.
- If package rename is chosen, provide compatibility shims and migration notes.

7) Theme UX overhaul aligned with Textual docs
- Add toolbar theme option.
- Keep command palette theme actions (including Textual's built-in `Theme` command via `super().get_system_commands`).
- Use App.available_themes and persisted settings.
- Remove private widget internals (no OptionList._options usage); use public OptionList methods/properties.
- Ensure the quick-cycle sequence exactly includes the design-guide example themes in this order:
  `nord`, `gruvbox`, `tokyo-night`, `textual-dark`, `solarized-light`, `atom-one-dark`, `atom-one-light`.
- Ensure CSS uses theme variables for legibility.

8) Events panel must contain CLI transcript
- Include lifecycle output and backend process output.
- Keep panel scrollable for long output.
- No terminal flood outside Events while TUI is active.

Validation checklist (must run and report):
- Launch TUI and verify Events receives lifecycle + backend output.
- Verify capability tabs show accurate counts/rows when capabilities exist.
- Quit TUI and verify shell input is immediately visible.
- Run --no-tui and verify first Ctrl+C triggers clean shutdown.
- Verify no shutdown cancel-scope runtime errors in logs.
- Verify no stale MCP Gateway / MCP_Bridge_Server strings in user-facing docs/help.
- Verify command palette still exposes Theme change and toolbar theme option works.
- Verify quick-cycle order matches Textual design-guide example theme sequence.

Deliverables:
- File-by-file change summary.
- Exact test/validation commands run.
- Key observed outputs proving each requirement.
- Remaining risks and follow-up actions.
```

---

## What Was Not Changed in This Audit

- No source code behavior was modified.
- This deliverable is analysis + implementation instructions only.
