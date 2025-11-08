# Implementation Plan

Short-term milestones to turn the design docs into a runnable TUI.

## Milestone 1 — Project Bootstrap
- Initialize uv-managed Python package (`uv init`, `pyproject.toml`).
- Document standard `uv run` commands for format, lint, test, and dev (avoid requiring extra task runners).
- Add base dependencies: `textual`, `rich`, `asyncpg`, `sqlglot`, `pydantic`, `structlog`, `ruff`, `pytest`.
- Lay down package skeleton `psqlui/` with `__init__.py`, config loader stub, and Textual app placeholder.
- Configure tooling: `ruff.toml`, `pyproject` scripts, formatting rules.
- Deliverable: repo runs `uv run textual run psqlui.app:main` (placeholder screen) + `uv run pytest` (empty suite).

## Milestone 2 — SQL Intelligence Foundations
- Implement `SqlIntelService` scaffold (interfaces, dataclasses, debounce helpers).
- Integrate `sqlglot` parsing, add keyword catalog, stub metadata adapters.
- Write unit tests for analysis + suggestion ranking (use sample buffers).
- Wire service into Textual query pad placeholder to confirm round-trip.

## Milestone 3 — Plugin Loader Prototype
- Implement entry-point discovery using `importlib.metadata`.
- Define `PluginContext`, capability protocols, and loader lifecycle per `plugin_contract.md`.
- Provide sample "hello world" plugin under `examples/plugins/` for manual testing.
- Add contract tests in CI ensuring plugins register cleanly.

## Milestone 4 — Navigation & Data Basics
- Flesh out Textual layout (sidebar, query pad, status bar).
- Build connection/session manager, integrate with config profiles.
- Display schemas/tables pulled via metadata cache (no editing yet).

## Tracking & Next Steps
- Update this file + `design/progress_log.md` after each milestone.
- Jot a brief note in `design/progress_log.md` at the end of every coding session/commit so future runs inherit the latest context.
- Use git tags (`milestone-1`, etc.) to mark major checkpoints.
