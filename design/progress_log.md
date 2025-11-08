# Progress Log

Snapshot of key decisions, artifacts, and next actions so the project can resume quickly in a fresh LLM session.

## Current Baseline
- **Repository root**: `/home/ipd21/psqlui`
- **Primary branch**: `main`
- **Latest commit**: `7e04a02` — Surface hello world plugin via palette
- **Uncommitted work**: Plugin pane contributions + sidebar host (`psqlui/app.py`, `psqlui/plugins/loader.py`, `psqlui/plugins/providers.py`), sample plugin updates/tests, README note, and this progress log update.

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

## Outstanding Tasks
- Continue Milestone 3 by exposing enable/disable controls in-app, persisting plugin settings, and adding richer sample capabilities (exporters, metadata hooks).
- Flesh out Textual spike (Milestone 4): persistent sidebar/query pad layout, command palette, status bar, basic session wiring.
- Connect SQL intel to the future metadata cache once the connection/session manager lands.
- Track dev workflow docs + onboarding guides alongside code changes.

## How to Resume
1. `cd /home/ipd21/psqlui`
2. `git status` (expect `design/sql_intelligence.md`, `design/plugin_contract.md`, `design/README.md`, `design/architecture.md`).
3. Continue editing or run `git commit -am "Document SQL intel and plugin contract"` once satisfied.

Keep this file updated whenever major decisions land so future contexts know the state of play.
## Update Ritual
- Before wrapping a session or committing, jot the latest commit hash, highlights, and TODOs here so the next run starts with context.
- Mention whether the working tree is clean or list uncommitted files to avoid surprises.
