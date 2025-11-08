# Progress Log

Snapshot of key decisions, artifacts, and next actions so the project can resume quickly in a fresh LLM session.

## Current Baseline
- **Repository root**: `/home/ipd21/psqlui`
- **Primary branch**: `main`
- **Latest commit**: Add agent runbook and update progress log (documented agent SOP + log refresh)
- **Uncommitted work**: AGENTS.md edit (ban `UV_CACHE_DIR`) + progress log adjustment.

## Completed So Far
1. Created `design/` hub with product overview, architecture, UI flows, roadmap, and ops/quality strategy.
2. Captured top-level product decisions (lean core, plugin-friendly advanced features, no telemetry, pagination focus, mouse support, layout persistence).
3. Documented SQL intelligence plan (client-side parsing, autocomplete, linting, caching, API surface).
4. Drafted plugin contract covering discovery, lifecycle, capabilities, and trust model.
5. Added `design/implementation_plan.md` describing near-term milestones (bootstrap, SQL intelligence foundation, plugin loader, navigation/data basics).
6. Completed Milestone 1 bootstrap: uv-managed project scaffold (`pyproject.toml`, `uv.lock`, `psqlui/` package, Textual placeholder app, tests, tooling config).
7. Completed Milestone 2 foundations: `SqlIntelService`, keyword/function/snippet catalogs, static metadata provider with refresh hooks, lint rules, Textual query pad integration (with metadata cycling and suggestion preview), and async unit tests covering analysis/suggestions/linting.
8. Added `AGENTS.md` runbook capturing agent-specific instructions (read progress log first, avoid running the TUI interactively, prefer uv commands, update docs each session, never override `UV_CACHE_DIR`, request elevated permissions for out-of-sandbox writes).

## Outstanding Tasks
- Prototype plugin loader/registry (Milestone 3): entry-point discovery, `PluginContext`, capability wiring, sample plugin + tests.
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
