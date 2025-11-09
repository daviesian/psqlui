# Progress Log

Snapshot of key decisions, artifacts, and next actions so the project can resume quickly in a fresh LLM session.

## Current Baseline
- **Repository root**: `/home/ipd21/psqlui`
- **Primary branch**: `main`
- **Latest commit**: `b1e8bfc` — Ensure resize handle spans full height
- **Uncommitted work**: Inline profile picker context menu + sidebar handle affordances (widgets/session/tests/progress log updates) and this progress log entry.

## Completed So Far
1. Created `design/` hub with product overview, architecture, UI flows, roadmap, and ops/quality strategy.
2. Captured top-level product decisions (lean core, plugin-friendly advanced features, no telemetry, pagination focus, mouse support, layout persistence).
3. Documented SQL intelligence plan (client-side parsing, autocomplete, linting, caching, API surface).
4. Drafted plugin contract covering discovery, lifecycle, capabilities, and trust model.
5. Added `design/implementation_plan.md` describing near-term milestones (bootstrap, SQL intelligence foundation, plugin loader, navigation/data basics).
6. Completed Milestone 1 bootstrap: uv-managed project scaffold (`pyproject.toml`, `uv.lock`, `psqlui/` package, Textual placeholder app, tests, tooling config).
7. Completed Milestone 2 foundations: `SqlIntelService`, keyword/function/snippet catalogs, static metadata provider with refresh hooks, lint rules, Textual query pad integration (with metadata cycling and suggestion preview), and async unit tests covering analysis/suggestions/linting.
8. Added `AGENTS.md` runbook capturing agent-specific instructions (read progress log first, avoid running the TUI interactively, prefer uv commands, update docs each session, never override `UV_CACHE_DIR`, request elevated permissions for out-of-sandbox writes).
9. Prototyped the plugin loader: capability dataclasses, `PluginContext`, entry-point discovery/registration, example `hello-world` plugin, and pytest coverage around discovery/load/shutdown paths.
10. Extended config with plugin enablement flags, patched `PluginLoader` filtering, initialized the loader inside `PsqluiApp` (with shutdown hook), and added regression tests for config helpers plus app-level loading/disablement.
11. Added a plugin command registry, registered plugin command capabilities during app startup, and covered the new path with registry + integration tests.
12. Integrated plugin commands into Textual's command palette via a custom provider, exported it from the plugin package, enhanced the sample plugin to track executions, and expanded tests to cover registry execution + provider hits.
13. Added builtin plugin discovery inside `PluginLoader` so the repo-shipped `hello-world` sample surfaces without packaging entry points, wired it through the app factory, and covered the flow with loader + app-level tests.
14. Mounted plugin pane capabilities in a sidebar container, updated the sample plugin to contribute a pane widget, and documented/validated the flow via README guidance plus pytest coverage.
15. Implemented TOML-based config loading from `~/.config/psqlui/config.toml`, including plugin enablement parsing and regression tests for happy/missing/error cases.
16. Added in-app plugin toggles via the command palette, config persistence helpers, and a developer doc outlining the contract.
17. Moved the plugin development guide under `docs/plugins.md` (user-facing), updated README references, and clarified agent guidance around `design/` vs `docs/` usage.
18. Kicked off Milestone 4 navigation/data work: extended config with connection profiles, introduced a session manager feeding metadata to SQL intel, rebuilt the Textual layout with persistent nav + status bars, refreshed the query pad wiring, and added coverage for the new infrastructure.
19. Added a profile switch command provider that updates the session manager + config, letting users swap demo profiles from the command palette (with regression tests).
20. Introduced a `DemoConnectionBackend` that emits metadata snapshots, hooked Ctrl+R to refresh the active session, and expanded coverage (`tests/test_connections.py`, refreshed session tests).
21. Fixed the sidebar profile list so entries render reliably by pre-building `ListView` items during compose, avoiding the async mount issues that left the pane blank.
22. Added session refresh timestamps (shown in the status bar), wired the session manager to generate timezone-aware updates, and exposed a command-palette `Refresh active profile metadata` action alongside coverage.
23. Extended config with a `LayoutState` so sidebar width persists between runs, applied the stored width during compose, and covered the persistence helpers with config + app tests.
24. Fixed the sidebar resize handler to avoid calling a non-existent parent method (which previously caused the app to exit immediately when Textual emitted a resize event).
25. Upgraded the simulated connection backend to emit health/latency info so the session manager and status bar can surface realistic connection telemetry.
26. Rebuilt the navigation sidebar with a profile summary panel plus a draggable resize handle that persists width adjustments between runs.
27. Added hover/drag affordances to the sidebar resize handle, introduced an inline profile context menu with switch/refresh actions, and taught the session manager (and tests) to refresh non-active profiles.
28. Wired keyboard shortcuts ("m" / Shift+F10) into the profile list so the context menu is accessible without a mouse, including inline focus/escape handling so the popup behaves like a native terminal menu (with an on-screen hint beneath the profile list).

## Outstanding Tasks
- Continue Milestone 3 by adding richer sample capabilities (exporters, metadata hooks) and surfacing plugin errors/health in the UI.
- Finish Milestone 4 wiring by replacing the demo metadata stub with the real connection/session cache once that service lands.
- Connect SQL intel + plugins to the new connection backend events (propagate refresh/errors) as we swap in a real driver.
- Track dev workflow docs + onboarding guides alongside code changes.

## How to Resume
1. `cd /home/ipd21/psqlui`
2. `git status` (expect config/app/widget/test updates and this log).
3. Continue editing or start a commit capturing the layout persistence work once ready.

Keep this file updated whenever major decisions land so future contexts know the state of play.
## Update Ritual
- Before wrapping a session or committing, jot the latest commit hash, highlights, and TODOs here so the next run starts with context.
- Mention whether the working tree is clean or list uncommitted files to avoid surprises.
