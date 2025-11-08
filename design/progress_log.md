# Progress Log

Snapshot of key decisions, artifacts, and next actions so the project can resume quickly in a fresh LLM session.

## Current Baseline
- **Repository root**: `/home/ipd21/psqlui`
- **Primary branch**: `main`
- **Latest commit**: `d46f4fb` — "Add SQL intel scaffold and wire into query pad" (SqlIntelService, metadata stub, query pad wiring, async tests)
- **Uncommitted work**: _none (clean tree after latest commit)._

## Completed So Far
1. Created `design/` hub with product overview, architecture, UI flows, roadmap, and ops/quality strategy.
2. Captured top-level product decisions (lean core, plugin-friendly advanced features, no telemetry, pagination focus, mouse support, layout persistence).
3. Documented SQL intelligence plan (client-side parsing, autocomplete, linting, caching, API surface).
4. Drafted plugin contract covering discovery, lifecycle, capabilities, and trust model.
5. Added `design/implementation_plan.md` describing near-term milestones (bootstrap, SQL intelligence foundation, plugin loader, navigation/data basics).
6. Completed Milestone 1 bootstrap: uv-managed project scaffold (`pyproject.toml`, `uv.lock`, `psqlui/` package, Textual placeholder app, tests, tooling config).
7. Started Milestone 2: implemented `SqlIntelService`, keyword catalog, static metadata provider, lint rules, Textual query pad integration, and async unit tests exercising analysis + suggestions.

## Outstanding Tasks
- Enrich SQL intelligence features: hook up real metadata cache, expand rule/suggestion coverage, expose APIs to plugins.
- Prototype plugin loader/registry to validate capability wiring.
- Flesh out Textual spike (sidebar, command palette, status) to host SQL intel output in the real query editor.
- Track dev workflow docs + onboarding guides alongside code changes.

## How to Resume
1. `cd /home/ipd21/psqlui`
2. `git status` (expect `design/sql_intelligence.md`, `design/plugin_contract.md`, `design/README.md`, `design/architecture.md`).
3. Continue editing or run `git commit -am "Document SQL intel and plugin contract"` once satisfied.

Keep this file updated whenever major decisions land so future contexts know the state of play.
## Update Ritual
- Before wrapping a session or committing, jot the latest commit hash, highlights, and TODOs here so the next run starts with context.
- Mention whether the working tree is clean or list uncommitted files to avoid surprises.
